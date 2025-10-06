from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from products.models import Product
from .models import Wishlist
import json

@login_required
def wishlist_view(request):
    """Display user's wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    context = {
        'wishlist_items': wishlist_items,
        'total_items': wishlist_items.count()
    }
    return render(request, 'wishlist/list.html', context)

@login_required
@require_POST
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Check if already in wishlist
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if created:
            return JsonResponse({
                'success': True,
                'message': f'{product.name} added to wishlist!',
                'in_wishlist': True,
                'wishlist_count': request.user.wishlist_items.count()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'{product.name} is already in your wishlist!',
                'in_wishlist': True,
                'wishlist_count': request.user.wishlist_items.count()
            })
    
    # Handle regular form submission
    if created:
        messages.success(request, f'{product.name} added to your wishlist!')
    else:
        messages.info(request, f'{product.name} is already in your wishlist!')
    
    return redirect('products:detail', slug=product.slug)

@login_required
@require_POST
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    
    try:
        wishlist_item = Wishlist.objects.get(user=request.user, product=product)
        wishlist_item.delete()
        
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'{product.name} removed from wishlist!',
                'in_wishlist': False,
                'wishlist_count': request.user.wishlist_items.count()
            })
        
        messages.success(request, f'{product.name} removed from your wishlist!')
        
    except Wishlist.DoesNotExist:
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'{product.name} is not in your wishlist!',
                'in_wishlist': False,
                'wishlist_count': request.user.wishlist_items.count()
            })
        
        messages.error(request, f'{product.name} is not in your wishlist!')
    
    # Redirect back to the referring page or wishlist
    return redirect(request.META.get('HTTP_REFERER', 'wishlist:list'))

@login_required
def toggle_wishlist(request, product_id):
    """Toggle product in/out of wishlist (AJAX endpoint)"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    try:
        wishlist_item = Wishlist.objects.get(user=request.user, product=product)
        wishlist_item.delete()
        in_wishlist = False
        message = f'{product.name} removed from wishlist!'
    except Wishlist.DoesNotExist:
        Wishlist.objects.create(user=request.user, product=product)
        in_wishlist = True
        message = f'{product.name} added to wishlist!'
    
    return JsonResponse({
        'success': True,
        'message': message,
        'in_wishlist': in_wishlist,
        'wishlist_count': request.user.wishlist_items.count()
    })

@login_required
def clear_wishlist(request):
    """Clear all items from wishlist"""
    if request.method == 'POST':
        count = request.user.wishlist_items.count()
        request.user.wishlist_items.all().delete()
        messages.success(request, f'Cleared {count} items from your wishlist!')
    
    return redirect('wishlist:list')
