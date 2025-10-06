# Additional view functions to be added to orders/views.py

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import Order

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
