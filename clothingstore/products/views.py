from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal
from .models import Product, Category

def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
    categories = Category.objects.filter(is_active=True)
    
    # Filter by category
    category_param = request.GET.get('category')
    if category_param:
        if ',' in category_param:
            # Multiple categories
            category_slugs = category_param.split(',')
            products = products.filter(category__slug__in=category_slugs)
        else:
            # Single category
            products = products.filter(category__slug=category_param)
    
    # Search functionality
    query = request.GET.get('search') or request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Price range filter
    price_range = request.GET.get('price_range')
    if price_range:
        if price_range == '0-25':
            products = products.filter(price__lte=25)
        elif price_range == '25-50':
            products = products.filter(price__gte=25, price__lte=50)
        elif price_range == '50-100':
            products = products.filter(price__gte=50, price__lte=100)
        elif price_range == '100+':
            products = products.filter(price__gte=100)
    
    # Size filter
    sizes_param = request.GET.get('sizes')
    if sizes_param:
        sizes = sizes_param.split(',')
        # Filter products that have any of the selected sizes
        size_queries = Q()
        for size in sizes:
            size_queries |= Q(available_sizes__contains=size)
        products = products.filter(size_queries)
    
    # Sorting
    sort_param = request.GET.get('sort')
    if sort_param:
        if sort_param == 'name':
            products = products.order_by('name')
        elif sort_param == '-name':
            products = products.order_by('-name')
        elif sort_param == 'price':
            products = products.order_by('price')
        elif sort_param == '-price':
            products = products.order_by('-price')
        elif sort_param == '-created_at':
            products = products.order_by('-created_at')
        else:
            products = products.order_by('-created_at', 'name')
    else:
        products = products.order_by('-created_at', 'name')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Size choices for filter
    size_choices = Product.SIZE_CHOICES
    
    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'categories': categories,
        'current_category': category_param,
        'query': query,
        'size_choices': size_choices,
        'current_sort': sort_param,
        'current_price_range': price_range,
        'current_sizes': sizes_param.split(',') if sizes_param else [],
    }
    return render(request, 'products/list.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related_products = Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)[:4]
    
    # Get the first image as the main image
    main_image = product.images.filter(is_primary=True).first()
    
    # Get all other images
    other_images = product.images.exclude(id=main_image.id if main_image else None)
    
    context = {
        'product': product,
        'main_image': main_image,
        'other_images': other_images,
        'related_products': related_products,
    }
    return render(request, 'products/detail.html', context)