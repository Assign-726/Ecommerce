# cart/views.py
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.template.loader import render_to_string
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from products.models import Product
from .models import Cart, CartItem, Coupon, AppliedCoupon

def get_or_create_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart

@login_required
@require_POST
def add_to_cart(request):
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    size = request.POST.get('size', '')
    color = request.POST.get('color', '')
    
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request.user)
    
    # Validate size selection if the product has size-specific inventory
    try:
        available_sizes = product.available_sizes  # list like ["S", "M", ...]
    except Exception:
        available_sizes = []
    
    if available_sizes:
        # Product expects a size; ensure a valid one is provided
        if not size:
            error_msg = 'Please select a size before adding to cart.'
            if request.headers.get('HX-Request'):
                return JsonResponse({'success': False, 'message': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('products:detail', slug=product.slug)
        if size not in available_sizes:
            error_msg = 'Selected size is not available for this product.'
            if request.headers.get('HX-Request'):
                return JsonResponse({'success': False, 'message': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('products:detail', slug=product.slug)
    
    # Check if item with same product, size and color already exists
    cart_item = CartItem.objects.filter(
        cart=cart,
        product=product,
        size=size,
        color=color
    ).first()
    
    if cart_item:
        # Update existing item
        cart_item.quantity += quantity
        cart_item.save()
        created = False
    else:
        # Create new item
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            size=size,
            color=color
        )
        created = True
    
    if request.headers.get('HX-Request'):
        return render(request, 'cart/partials/cart_count.html', {'cart': cart})
    
    messages.success(request, f'{product.name} added to cart!')
    return redirect('products:detail', slug=product.slug)

@login_required
def cart_detail(request):
    # Get or create cart and force refresh from database
    cart = get_or_create_cart(request.user)
    cart.refresh_from_db()
    
    # Get applied coupon if exists
    try:
        applied_coupon = AppliedCoupon.objects.select_related('coupon').get(cart=cart)
        # Debug output
        print(f"Found applied coupon: {applied_coupon.coupon.code} with discount: {applied_coupon.discount_amount}")
    except AppliedCoupon.DoesNotExist:
        applied_coupon = None
        print("No coupon applied to this cart")
    
    # Debug output
    print(f"Cart total: {cart.total_price}")
    print(f"Cart subtotal: {cart.subtotal_price}")
    print(f"Cart discount: {cart.discount_amount}")
    
    context = {
        'cart': cart,
        'applied_coupon': applied_coupon
    }
    return render(request, 'cart/detail.html', context)

@login_required
@require_POST
def update_cart_item(request):
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))
    
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()
    
    if request.headers.get('HX-Request'):
        cart = cart_item.cart
        return render(request, 'cart/partials/cart_items.html', {'cart': cart})
    
    return redirect('cart:detail')

@login_required
@require_POST
def remove_from_cart(request):
    item_id = request.POST.get('item_id')
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    
    if request.headers.get('HX-Request'):
        cart = get_or_create_cart(request.user)
        return render(request, 'cart/partials/cart_items.html', {'cart': cart})
    
    return redirect('cart:detail')

@login_required
@require_http_methods(['POST'])
def apply_coupon(request):
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'valid': False, 'message': 'Authentication required'}, status=401)
        messages.error(request, 'Please log in to apply a coupon')
        return redirect('account_login')
        
    code = request.POST.get('coupon_code', '').strip().upper()
    if not code:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'valid': False, 'message': 'Please enter a coupon code'})
        messages.error(request, 'Please enter a coupon code')
        return redirect('cart:detail')
    
    cart = get_or_create_cart(request.user)
    
    try:
        print(f"[DEBUG] Attempting to apply coupon: {code}")
        print(f"[DEBUG] Cart subtotal before coupon: {cart.subtotal_price}")
        
        # Get the coupon (case-insensitive match)
        try:
            coupon = Coupon.objects.get(code__iexact=code, is_active=True)
            print(f"[DEBUG] Found coupon: {coupon.code} (ID: {coupon.id})")
            print(f"[DEBUG] Coupon details: {coupon.discount_type}, {coupon.discount_value}, Min: {coupon.min_order_amount}")
        except Coupon.DoesNotExist:
            message = 'Invalid coupon code. Please check and try again.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'valid': False, 'message': message}, status=400)
            messages.error(request, message)
            return redirect('cart:detail')
        
        # Validate coupon using subtotal_price to avoid recursion
        is_valid, message = coupon.is_valid(request.user, float(cart.subtotal_price), return_reason=True)
        print(f"[DEBUG] Coupon validation - Valid: {is_valid}, Message: {message}")
        
        if not is_valid:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'valid': False, 'message': message}, status=400)
            messages.error(request, message)
            return redirect('cart:detail')
        
        # Calculate discount using subtotal (before any discounts)
        discount_amount = float(coupon.calculate_discount(float(cart.subtotal_price)))
        print(f"[DEBUG] Calculated discount: {discount_amount} for cart subtotal: {cart.subtotal_price}")
        
        # Start transaction
        with transaction.atomic():
            # Remove any existing applied coupon
            AppliedCoupon.objects.filter(cart=cart).delete()
            
            # Apply new coupon
            applied_coupon = AppliedCoupon.objects.create(
                coupon=coupon,
                user=request.user,
                cart=cart,
                discount_amount=discount_amount
            )
            print(f"[DEBUG] Created AppliedCoupon: {applied_coupon.id}")
            
            # Update coupon usage
            coupon.times_used = F('times_used') + 1
            coupon.save(update_fields=['times_used'])
            
            # Refresh coupon to get updated times_used
            coupon.refresh_from_db()
            
            # Force refresh cart and related data
            cart = Cart.objects.select_related('applied_coupon__coupon').get(id=cart.id)
            print(f"[DEBUG] Cart after coupon - "
                  f"Subtotal: {cart.subtotal_price}, "
                  f"Discount: {discount_amount}, "
                  f"Total: {cart.total_price}")
            
            success_message = f'Coupon {code} applied successfully! Discount: ₹{discount_amount:,.2f} applied to your order.'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Render the order summary partial to include in the response
                order_summary_html = render_to_string('cart/partials/order_summary.html', {
                    'cart': cart,
                    'applied_coupon': cart.applied_coupon,
                    'request': request  # Make sure request is available in the template
                })
                
                return JsonResponse({
                    'valid': True,
                    'message': success_message,
                    'discount_amount': float(discount_amount),
                    'discount_formatted': f'₹{discount_amount:,.2f}',
                    'total_after_discount': float(cart.total_price),
                    'order_summary_html': order_summary_html,
                    'coupon_code': code
                })
            
        messages.success(request, success_message)
        
    except Exception as e:
        print(f"[ERROR] Error applying coupon: {str(e)}")
        import traceback
        traceback.print_exc()
        error_message = 'An error occurred while applying the coupon. Please try again or contact support.'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'valid': False, 'message': error_message}, status=400)
            
        messages.error(request, error_message)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'valid': False, 'message': 'An unexpected error occurred'}, status=500)
        
    return redirect('cart:detail')

@login_required
@require_http_methods(['POST'])
def remove_coupon(request):
    cart = get_or_create_cart(request.user)
    
    try:
        with transaction.atomic():
            # Get and lock the applied coupon
            applied_coupon = AppliedCoupon.objects.select_for_update().get(cart=cart)
            coupon = applied_coupon.coupon
            
            # Store coupon code for message
            coupon_code = coupon.code
            
            # Remove the applied coupon first
            applied_coupon.delete()
            
            # Update coupon usage (ensure it doesn't go below 0)
            if coupon.times_used > 0:
                coupon.times_used = F('times_used') - 1
                coupon.save(update_fields=['times_used'])
            
            # Force refresh the cart with related data
            cart = Cart.objects.select_related('applied_coupon__coupon').get(id=cart.id)
            
            success_message = f'Coupon {coupon_code} has been removed from your cart.'
            messages.success(request, success_message)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Render the order summary partial to include in the response
                order_summary_html = render_to_string('cart/partials/order_summary.html', {
                    'cart': cart,
                    'applied_coupon': None
                })
                
                return JsonResponse({
                    'valid': True,
                    'message': success_message,
                    'order_summary_html': order_summary_html
                })
            
    except AppliedCoupon.DoesNotExist:
        error_message = 'No coupon is currently applied to your cart'
        messages.info(request, error_message)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'valid': False,
                'message': error_message
            }, status=400)
            
    except Exception as e:
        print(f"[ERROR] Error removing coupon: {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_message = 'An error occurred while removing the coupon. Please try again.'
        messages.error(request, error_message)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'valid': False,
                'message': error_message
            }, status=500)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # If we get here, it's a non-AJAX request that needs a redirect
        return JsonResponse({
            'redirect': reverse('cart:detail')
        })
        
    return redirect('cart:detail')

def validate_coupon_ajax(request):
    if not request.user.is_authenticated:
        return JsonResponse({'valid': False, 'message': 'Authentication required'}, status=401)
        
    code = request.GET.get('code', '').strip().upper()
    if not code:
        return JsonResponse({'valid': False, 'message': 'Please enter a coupon code'})
        
    cart = get_or_create_cart(request.user)
    
    try:
        # Get the coupon (case-insensitive match)
        coupon = Coupon.objects.get(code__iexact=code, is_active=True)
        
        # Use subtotal_price for validation to avoid recursion
        is_valid, message = coupon.is_valid(request.user, float(cart.subtotal_price))
        
        if is_valid:
            discount_amount = float(coupon.calculate_discount(cart.subtotal_price))
            return JsonResponse({
                'valid': True,
                'message': 'Coupon applied successfully!',
                'discount': discount_amount,
                'discount_formatted': f'₹{discount_amount:,.2f}',
                'code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': float(coupon.discount_value),
                'min_order_amount': float(coupon.min_order_amount) if coupon.min_order_amount else 0
            })
        else:
            return JsonResponse({
                'valid': False, 
                'message': message or 'This coupon is not valid for your cart.'
            })
            
    except Coupon.DoesNotExist:
        return JsonResponse({
            'valid': False, 
            'message': 'Invalid coupon code. Please check and try again.'
        })
    except Exception as e:
        print(f"[ERROR] Error validating coupon: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'valid': False,
            'message': 'An error occurred while validating the coupon. Please try again.'
        }, status=500)