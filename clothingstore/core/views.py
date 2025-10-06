from django.shortcuts import render
from products.models import Product, Category
from .models import Banner

def home(request):
    featured_products = Product.objects.filter(is_featured=True, is_active=True)[:8]
    categories = Category.objects.filter(is_active=True)[:6]
    active_banners = Banner.objects.filter(is_active=True).order_by('order', '-created_at')
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'banners': active_banners,
    }
    return render(request, 'core/home.html', context)