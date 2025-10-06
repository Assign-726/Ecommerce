# orders/views.py
import uuid
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from cart.models import Cart
from .models import Order, OrderItem

import razorpay
import logging

# Set up logging
logger = logging.getLogger(__name__)

def get_razorpay_client():
    """Initialize and return Razorpay client using settings keys (test or live)."""
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_t3dbQtsUI9wNjh')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', None)
    if not key_secret:
        raise ValueError('RAZORPAY_KEY_SECRET is not configured in settings.')
    return razorpay.Client(auth=(key_id, key_secret))

@login_required
def checkout(request):
    """
    Handle the checkout process and create a Razorpay order
    """
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart:detail')
    
    if request.method == 'POST':
        try:
            # Create order
            order = Order.objects.create(
                user=request.user,
                order_number=str(uuid.uuid4())[:8].upper(),
                total_amount=cart.total_price,
                shipping_name=request.POST.get('shipping_name'),
                shipping_email=request.POST.get('shipping_email'),
                shipping_phone=request.POST.get('shipping_phone'),
                shipping_address=request.POST.get('shipping_address'),
                shipping_city=request.POST.get('shipping_city'),
                shipping_state=request.POST.get('shipping_state'),
                shipping_zip_code=request.POST.get('shipping_zip_code'),
                shipping_country=request.POST.get('shipping_country', 'IN'),
                payment_status='pending',
                status='pending'
            )
            
            # Create order items
            order_items = []
            for cart_item in cart.items.all():
                order_item = OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.get_price,
                    size=cart_item.size,
                    color=getattr(cart_item, 'color', ''),
                )
                order_items.append(order_item)
            
            # Prepare Razorpay order data
            amount_paise = int(order.total_amount * 100)  # Convert to paise

            # Always create a Razorpay order (uses test keys if configured)
            try:
                client = get_razorpay_client()
                razorpay_order = client.order.create({
                    'amount': amount_paise,
                    'currency': 'INR',
                    'receipt': f'order_{order.order_number}',
                    'payment_capture': 1
                })

                # Update order with Razorpay details
                order.razorpay_order_id = razorpay_order['id']
                order.save()

                context = {
                    'order': order,
                    'amount_paise': amount_paise,
                    'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_t3dbQtsUI9wNjh'),
                    'customer_name': order.shipping_name,
                    'customer_email': order.shipping_email,
                    'customer_phone': order.shipping_phone,
                    'debug': settings.DEBUG,
                }

                # Do NOT clear cart here; clear it after payment verification
                return render(request, 'orders/payment.html', context)

            except Exception as e:
                logger.error(f"Error creating Razorpay order: {str(e)}")
                messages.error(request, 'Error setting up payment. Please try again.')
                return redirect('cart:detail')
                
        except Exception as e:
            logger.error(f"Error during checkout: {str(e)}")
            messages.error(request, 'An error occurred during checkout. Please try again.')
            return redirect('cart:detail')
    
    # GET request: prefill from saved profile
    profile = getattr(request.user, 'profile', None)
    initial = {}
    if profile:
        full_name = (f"{request.user.first_name} {request.user.last_name}" ).strip() or request.user.username
        address = profile.address_line1 or ''
        if profile.address_line2:
            address = f"{address} {profile.address_line2}".strip()
        initial = {
            'shipping_name': full_name,
            'shipping_email': request.user.email or '',
            'shipping_phone': profile.phone_number or '',
            'shipping_address': address,
            'shipping_city': profile.city or '',
            'shipping_state': profile.state or '',
            'shipping_zip_code': profile.postal_code or '',
            'shipping_country': profile.country or 'IN',
        }
    context = {
        'cart': cart,
        'initial': initial,
    }
    return render(request, 'orders/checkout.html', context)

@csrf_exempt
def razorpay_verify(request):
    """
    Verify Razorpay payment and update order status
    """
    if request.method != 'POST':
        return JsonResponse(
            {'status': 'error', 'message': 'Only POST method is allowed'},
            status=405
        )
    
    # Get payment details from request
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')
    
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return JsonResponse(
            {'status': 'error', 'message': 'Missing payment details'},
            status=400
        )
    
    try:
        # Get the order from the database
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id, user=request.user)
        except Order.DoesNotExist:
            logger.error(f'Order not found for Razorpay order ID: {razorpay_order_id}')
            return JsonResponse({
                'status': 'error',
                'message': 'Order not found. Please contact support with order details.'
            }, status=404)
        
        # Always verify the signature (works with test or live keys)
        try:
            client = get_razorpay_client()
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify the payment signature
            client.utility.verify_payment_signature(params_dict)
            
            # Update order status
            order.payment_status = 'completed'
            order.status = 'processing'
            order.payment_id = razorpay_payment_id
            order.payment_method = 'razorpay'
            order.payment_details = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            order.save()
            
            logger.info(f'Payment successful for order {order.order_number}')
            
            # Clear the user's cart
            Cart.objects.filter(user=request.user).delete()
            
            # Return success response with redirect URL
            return JsonResponse({
                'status': 'success',
                'message': 'Payment verified successfully',
                'order_number': order.order_number,
                'redirect_url': reverse('orders:order_success', kwargs={'order_number': order.order_number})
            })
            
        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f'Razorpay signature verification failed for order {order.order_number}: {str(e)}')
            
            # Update order status to reflect payment failure
            order.payment_status = 'failed'
            order.status = 'payment_failed'
            order.save()
            
            return JsonResponse({
                'status': 'error',
                'message': 'Payment verification failed: Invalid signature. Please contact support if the amount was deducted.'
            }, status=400)
            
        except Exception as e:
            logger.error(f'Error verifying Razorpay payment for order {order.order_number}: {str(e)}')
            
            # Update order status to reflect payment verification error
            order.payment_status = 'failed'
            order.status = 'payment_error'
            order.save()
            
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while verifying your payment. Our team has been notified.'
            }, status=500)
            
    except Exception as e:
        logger.error(f'Unexpected error in razorpay_verify: {str(e)}', exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred. Please contact support with your order details.'
        }, status=500)

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'orders/list.html', {'orders': orders})

@login_required
def order_success(request, order_number):
    """
    Display order success page with order details
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Prepare context
    context = {
        'order': order,
        'items': order.items.all(),
        'is_test_mode': settings.DEBUG,
        'payment_method': 'Test Mode' if settings.DEBUG else 'Razorpay',
    }
    
    # In test mode, simulate a successful payment if not already completed
    if settings.DEBUG and not order.payment_status == 'completed':
        order.payment_status = 'completed'
        order.status = 'processing'
        order.save()
    
    # Add payment status to context
    context.update({
        'is_payment_successful': order.payment_status == 'completed',
        'order_status_display': dict(Order.ORDER_STATUS_CHOICES).get(order.status, order.status),
        'payment_status_display': 'Paid' if order.payment_status == 'completed' else 'Pending'
    })
    
    return render(request, 'orders/order_success.html', context)

@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/detail.html', {'order': order})

@login_required
@require_POST
def cancel_order(request, order_number):
    """Allow users to cancel their orders if they are in pending or processing status"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Only allow cancellation for pending or processing orders
    if order.status in ['pending', 'processing']:
        order.status = 'cancelled'
        order.save()
        messages.success(request, f'Order #{order.order_number} has been cancelled successfully.')
    else:
        messages.error(request, 'This order cannot be cancelled as it has already been shipped or delivered.')
    
    return redirect('orders:detail', order_number=order.order_number)

@login_required
@require_POST  
def reorder(request, order_number):
    """Allow users to reorder items from a previous order"""
    from cart.models import Cart, CartItem
    
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Add all order items to cart
    items_added = 0
    for order_item in order.items.all():
        # Check if product is still available
        if order_item.product.stock > 0:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=order_item.product,
                size=order_item.size,
                defaults={'quantity': order_item.quantity}
            )
            if not created:
                cart_item.quantity += order_item.quantity
                cart_item.save()
            items_added += 1
    
    if items_added > 0:
        messages.success(request, f'{items_added} items from order #{order.order_number} have been added to your cart.')
        return redirect('cart:detail')
    else:
        messages.error(request, 'No items could be added to cart. Products may be out of stock.')
        return redirect('orders:detail', order_number=order.order_number)
