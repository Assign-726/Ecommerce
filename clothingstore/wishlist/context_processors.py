from .models import Wishlist

def wishlist_context(request):
    """
    Context processor to add wishlist data to all templates
    """
    context = {}
    
    if request.user.is_authenticated:
        # Get user's wishlist items
        wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
        wishlist_product_ids = list(wishlist_items.values_list('product_id', flat=True))
        
        context.update({
            'user_wishlist_items': wishlist_items,
            'user_wishlist_product_ids': wishlist_product_ids,
            'user_wishlist_count': wishlist_items.count(),
        })
    else:
        context.update({
            'user_wishlist_items': [],
            'user_wishlist_product_ids': [],
            'user_wishlist_count': 0,
        })
    
    return context
