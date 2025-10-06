# admin_dashboard/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime, timedelta
import json

from products.models import Product, Category, ProductImage, Size, ProductSize
from orders.models import Order, OrderItem
from django.contrib.auth.models import User
from cart.models import Cart, CartItem, Coupon, AppliedCoupon
from core.models import Banner
from django import forms
from django.utils import timezone
from datetime import datetime, timedelta

def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_staff_or_superuser)
def dashboard_home(request):
    """Main dashboard overview with statistics"""
    
    # Get date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Basic statistics
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()
    total_customers = User.objects.filter(is_staff=False).count()
    
    # Recent statistics
    recent_orders = Order.objects.filter(created_at__date__gte=week_ago).count()
    recent_customers = User.objects.filter(date_joined__date__gte=week_ago, is_staff=False).count()
    
    # Revenue statistics
    total_revenue = Order.objects.filter(status='completed').aggregate(
        total=Sum('total_amount'))['total'] or 0
    monthly_revenue = Order.objects.filter(
        created_at__date__gte=month_ago, 
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Low stock products
    low_stock_products = Product.objects.filter(stock__lte=10, is_active=True)[:5]
    
    # Recent orders
    recent_orders_list = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # Popular products
    popular_products = Product.objects.annotate(
        order_count=Count('order_items')
    ).order_by('-order_count')[:5]
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'recent_orders': recent_orders,
        'recent_customers': recent_customers,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'low_stock_products': low_stock_products,
        'recent_orders_list': recent_orders_list,
        'popular_products': popular_products,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def product_list(request):
    """Product management list view"""
    
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    products = Product.objects.select_related('category').prefetch_related('images')
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    elif status_filter == 'featured':
        products = products.filter(is_featured=True)
    elif status_filter == 'low_stock':
        products = products.filter(stock__lte=10)
    
    products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_dashboard/products/list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def product_create(request):
    """Create new product"""
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            slug = request.POST.get('slug')
            category_id = request.POST.get('category')
            description = request.POST.get('description')
            price = request.POST.get('price')
            discount_price = request.POST.get('discount_price') or None
            stock = request.POST.get('stock', 0)
            available_sizes = request.POST.getlist('available_sizes')
            available_colors = request.POST.getlist('available_colors')
            is_active = request.POST.get('is_active') == 'on'
            is_featured = request.POST.get('is_featured') == 'on'
            
            # Create product
            product = Product.objects.create(
                name=name,
                slug=slug,
                category_id=category_id,
                description=description,
                price=price,
                discount_price=discount_price,
                stock=stock,
                available_colors=available_colors,
                is_active=is_active,
                is_featured=is_featured
            )
            
            # Persist sizes into ProductSize with a simple quantity allocation
            try:
                stock_int = int(stock or 0)
            except (TypeError, ValueError):
                stock_int = 0
            sizes_qs = Size.objects.filter(is_active=True, name__in=available_sizes)
            if sizes_qs.exists():
                per_size_qty = max(1, (stock_int // sizes_qs.count()) if stock_int > 0 else 1)
                for s in sizes_qs:
                    ProductSize.objects.create(product=product, size=s, quantity=per_size_qty)
            
            # Handle images
            images = request.FILES.getlist('images')
            for i, image in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(i == 0)  # First image is primary
                )
            
            messages.success(request, f'Product "{name}" created successfully!')
            return redirect('admin_dashboard:product_list')
            
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
    
    categories = Category.objects.all()
    # Load active sizes from Size model (code, display)
    size_choices = [(s.name, s.display_name) for s in Size.objects.filter(is_active=True).order_by('order', 'name')]
    color_choices = Product.COLOR_CHOICES
    
    context = {
        'categories': categories,
        'size_choices': size_choices,
        'color_choices': color_choices,
    }
    
    return render(request, 'admin_dashboard/products/create.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def product_edit(request, product_id):
    """Edit existing product"""
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            # Update product data
            product.name = request.POST.get('name')
            product.slug = request.POST.get('slug')
            product.category_id = request.POST.get('category')
            product.description = request.POST.get('description')
            product.price = request.POST.get('price')
            product.discount_price = request.POST.get('discount_price') or None
            product.stock = request.POST.get('stock', 0)
            selected_sizes = request.POST.getlist('available_sizes')
            product.available_colors = request.POST.getlist('available_colors')
            product.is_active = request.POST.get('is_active') == 'on'
            product.is_featured = request.POST.get('is_featured') == 'on'
            product.save()
            
            # Sync ProductSize relations based on selected sizes
            try:
                stock_int = int(product.stock or 0)
            except (TypeError, ValueError):
                stock_int = 0
            current_ps = {ps.size.name: ps for ps in product.productsizes.select_related('size')}
            active_sizes = set(Size.objects.filter(is_active=True, name__in=selected_sizes).values_list('name', flat=True))
            
            # Delete unselected sizes
            for size_code, ps in list(current_ps.items()):
                if size_code not in active_sizes:
                    ps.delete()
            
            # Add new sizes with a minimal quantity if not present
            missing = active_sizes.difference(current_ps.keys())
            if missing:
                per_size_qty = max(1, (stock_int // max(1, len(active_sizes))) if stock_int > 0 else 1)
                for s in Size.objects.filter(name__in=missing):
                    ProductSize.objects.create(product=product, size=s, quantity=per_size_qty)
            
            # Handle new images
            images = request.FILES.getlist('images')
            for image in images:
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=not product.images.exists()  # First image is primary
                )
            
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('admin_dashboard:product_list')
            
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
    
    categories = Category.objects.all()
    # Load active sizes for selection
    size_choices = [(s.name, s.display_name) for s in Size.objects.filter(is_active=True).order_by('order', 'name')]
    color_choices = Product.COLOR_CHOICES
    
    # Ensure available_sizes is always a list
    if not hasattr(product, 'available_sizes') or not product.available_sizes:
        product.available_sizes = []
    # Ensure available_colors is always a list
    if not hasattr(product, 'available_colors') or not product.available_colors:
        product.available_colors = []
    
    context = {
        'product': product,
        'categories': categories,
        'size_choices': size_choices,
        'color_choices': color_choices,
    }
    
    return render(request, 'admin_dashboard/products/edit.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
@require_POST
def product_delete(request, product_id):
    """Delete product"""
    
    product = get_object_or_404(Product, id=product_id)
    product_name = product.name
    product.delete()
    
    messages.success(request, f'Product "{product_name}" deleted successfully!')
    return redirect('admin_dashboard:product_list')

@login_required
@user_passes_test(is_staff_or_superuser)
def category_list(request):
    """Category management list view"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete':
            category_id = request.POST.get('category_id')
            try:
                category = get_object_or_404(Category, id=category_id)
                category_name = category.name
                category.delete()
                messages.success(request, f'Category "{category_name}" has been deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting category: {str(e)}')
        
        elif action in [None, '']:  # Create or Edit category
            category_id = request.POST.get('category_id')
            name = request.POST.get('name')
            slug = request.POST.get('slug')
            description = request.POST.get('description', '')
            is_active = request.POST.get('is_active') == 'on'
            image = request.FILES.get('image')
            
            try:
                if category_id:  # Edit existing category
                    category = get_object_or_404(Category, id=category_id)
                    category.name = name
                    category.slug = slug
                    category.description = description
                    category.is_active = is_active
                    if image:
                        category.image = image
                    category.save()
                    messages.success(request, f'Category "{name}" has been updated successfully.')
                else:  # Create new category
                    category = Category.objects.create(
                        name=name,
                        slug=slug,
                        description=description,
                        is_active=is_active,
                        image=image if image else None
                    )
                    messages.success(request, f'Category "{name}" has been created successfully.')
            except Exception as e:
                messages.error(request, f'Error saving category: {str(e)}')
        
        return redirect('admin_dashboard:category_list')
    
    search_query = request.GET.get('search', '')
    categories = Category.objects.annotate(
        product_count=Count('products')
    )
    
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    categories = categories.order_by('name')
    
    # Pagination
    paginator = Paginator(categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'admin_dashboard/categories/list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def order_list(request):
    """Order management list view"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            order_id = request.POST.get('order_id')
            new_status = request.POST.get('status')
            tracking_number = request.POST.get('tracking_number', '')
            
            try:
                order = get_object_or_404(Order, id=order_id)
                order.status = new_status
                if tracking_number:
                    order.tracking_number = tracking_number
                order.save()
                messages.success(request, f'Order #{order_id} status updated to {new_status.title()}.')
            except Exception as e:
                messages.error(request, f'Error updating order status: {str(e)}')
        
        return redirect('admin_dashboard:order_list')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Get orders with related data
    orders = Order.objects.select_related('user').prefetch_related('items__product')
    
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(order_number__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    orders = orders.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_dashboard/orders/list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def order_detail_ajax(request, order_id):
    """AJAX endpoint to get order details"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Get order items
        items_data = []
        for item in order.items.all():
            items_data.append({
                'product_name': item.product.name,
                'quantity': item.quantity,
                'size': item.size,
                'price': float(item.price),
                'total': float(item.price * item.quantity),
                'image_url': item.product.images.first().image.url if item.product.images.exists() else None
            })
        
        data = {
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'total_amount': float(order.total_amount),
            'created_at': order.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'customer': {
                'name': f"{order.user.first_name} {order.user.last_name}".strip() or order.user.username,
                'email': order.user.email,
                'username': order.user.username,
            },
            'shipping': {
                'name': order.shipping_name,
                'email': order.shipping_email,
                'phone': order.shipping_phone,
                'address': order.shipping_address,
                'city': order.shipping_city,
                'state': order.shipping_state,
                'zip_code': order.shipping_zip_code,
                'country': order.shipping_country,
            },
            'items': items_data,
            'payment_status': order.payment_status,
        }
        
        return JsonResponse(data)
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
        
    except Exception as e:
        import traceback
        print(f"Error in order_detail_ajax: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'error': 'An error occurred while fetching order details',
            'details': str(e)
        }, status=500)

@login_required
@user_passes_test(is_staff_or_superuser)
def customer_list(request):
    """Customer management list view"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'edit_customer':
            customer_id = request.POST.get('customer_id')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email')
            is_active = request.POST.get('is_active') == 'on'
            is_staff = request.POST.get('is_staff') == 'on'
            
            try:
                customer = get_object_or_404(User, id=customer_id)
                customer.first_name = first_name
                customer.last_name = last_name
                customer.email = email
                customer.is_active = is_active
                customer.is_staff = is_staff
                customer.save()
                messages.success(request, f'Customer "{customer.username}" has been updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating customer: {str(e)}')
        
        elif action == 'toggle_status':
            customer_id = request.POST.get('customer_id')
            is_active = request.POST.get('is_active') == 'true'
            
            try:
                customer = get_object_or_404(User, id=customer_id)
                customer.is_active = is_active
                customer.save()
                status = 'activated' if is_active else 'deactivated'
                messages.success(request, f'Customer "{customer.username}" has been {status} successfully.')
            except Exception as e:
                messages.error(request, f'Error updating customer status: {str(e)}')
        
        return redirect('admin_dashboard:customer_list')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Try to get order count and total spent, but handle if Order model doesn't exist
    try:
        from orders.models import Order
        customers = User.objects.annotate(
            order_count=Count('order'),
            total_spent=Sum('order__total_amount')
        )
    except ImportError:
        # If Order model doesn't exist, just get users without annotations
        customers = User.objects.all()
        # Add default values for order_count and total_spent
        for customer in customers:
            customer.order_count = 0
            customer.total_spent = 0
    
    if search_query:
        customers = customers.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if status_filter == 'active':
        customers = customers.filter(is_active=True)
    elif status_filter == 'inactive':
        customers = customers.filter(is_active=False)
    elif status_filter == 'staff':
        customers = customers.filter(is_staff=True)
    
    customers = customers.order_by('-date_joined')
    
    # Pagination
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_dashboard/customers/list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def banner_list(request):
    """Banner management list view"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_status':
            banner_id = request.POST.get('banner_id')
            try:
                banner = get_object_or_404(Banner, id=banner_id)
                banner.is_active = not banner.is_active
                banner.save()
                status = 'activated' if banner.is_active else 'deactivated'
                messages.success(request, f'Banner "{banner.title}" has been {status}.')
            except Exception as e:
                messages.error(request, f'Error updating banner status: {str(e)}')
        
        elif action == 'delete_banner':
            banner_id = request.POST.get('banner_id')
            try:
                banner = get_object_or_404(Banner, id=banner_id)
                banner_title = banner.title
                banner.delete()
                messages.success(request, f'Banner "{banner_title}" has been deleted.')
            except Exception as e:
                messages.error(request, f'Error deleting banner: {str(e)}')
        
        return redirect('admin_dashboard:banner_list')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    banners = Banner.objects.all()
    
    if search_query:
        banners = banners.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if status_filter == 'active':
        banners = banners.filter(is_active=True)
    elif status_filter == 'inactive':
        banners = banners.filter(is_active=False)
    
    banners = banners.order_by('order', '-created_at')
    
    # Pagination
    paginator = Paginator(banners, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_dashboard/banners/list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def banner_create(request):
    """Create new banner"""
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description')
            image = request.FILES.get('image')
            animation_type = request.POST.get('animation_type', 'fade')
            animation_duration = int(request.POST.get('animation_duration', 3000))
            link_url = request.POST.get('link_url', '')
            link_text = request.POST.get('link_text', '')
            order = int(request.POST.get('order', 0))
            is_active = request.POST.get('is_active') == 'on'
            
            banner = Banner.objects.create(
                title=title,
                description=description,
                image=image,
                animation_type=animation_type,
                animation_duration=animation_duration,
                link_url=link_url if link_url else None,
                link_text=link_text,
                order=order,
                is_active=is_active
            )
            
            messages.success(request, f'Banner "{banner.title}" created successfully!')
            return redirect('admin_dashboard:banner_list')
            
        except Exception as e:
            messages.error(request, f'Error creating banner: {str(e)}')
    
    context = {
        'animation_choices': Banner.ANIMATION_CHOICES,
    }
    
    return render(request, 'admin_dashboard/banners/create.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def banner_edit(request, banner_id):
    """Edit existing banner"""
    
    banner = get_object_or_404(Banner, id=banner_id)
    
    if request.method == 'POST':
        try:
            banner.title = request.POST.get('title')
            banner.description = request.POST.get('description')
            
            if request.FILES.get('image'):
                banner.image = request.FILES.get('image')
            
            banner.animation_type = request.POST.get('animation_type', 'fade')
            banner.animation_duration = int(request.POST.get('animation_duration', 3000))
            banner.link_url = request.POST.get('link_url', '') or None
            banner.link_text = request.POST.get('link_text', '')
            banner.order = int(request.POST.get('order', 0))
            banner.is_active = request.POST.get('is_active') == 'on'
            
            banner.save()
            
            messages.success(request, f'Banner "{banner.title}" updated successfully!')
            return redirect('admin_dashboard:banner_list')
            
        except Exception as e:
            messages.error(request, f'Error updating banner: {str(e)}')
    
    context = {
        'banner': banner,
        'animation_choices': Banner.ANIMATION_CHOICES,
    }
    
    return render(request, 'admin_dashboard/banners/edit.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def banner_delete(request, banner_id):
    """Delete banner"""
    
    banner = get_object_or_404(Banner, id=banner_id)
    
    if request.method == 'POST':
        try:
            banner_name = banner.title
            banner.delete()
            messages.success(request, f'Banner "{banner_name}" deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting banner: {str(e)}')
    
    return redirect('admin_dashboard:banner_list')

@login_required
@user_passes_test(is_staff_or_superuser)
@require_POST
def delete_product_image(request):
    """Delete a product image via AJAX"""
    try:
        image_id = request.POST.get('image_id')
        if not image_id:
            return JsonResponse({'success': False, 'message': 'Image ID is required'}, status=400)
            
        image = get_object_or_404(ProductImage, id=image_id)
        product_id = image.product.id
        image.delete()
        
        # If this was the primary image and there are other images, set the first one as primary
        product = get_object_or_404(Product, id=product_id)
        if product.images.exists() and not product.images.filter(is_primary=True).exists():
            first_image = product.images.first()
            first_image.is_primary = True
            first_image.save()
            
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@user_passes_test(is_staff_or_superuser)
@require_POST
def set_primary_image(request):
    """Set an image as primary for a product via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            image_id = data.get('image_id')
            
            # Get the image and its product
            image = ProductImage.objects.get(id=image_id)
            product = image.product
            
            # Update all images of this product to set is_primary=False
            ProductImage.objects.filter(product=product).update(is_primary=False)
            
            # Set the selected image as primary
            image.is_primary = True
            image.save()
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

# Coupon Management Views
@login_required
@user_passes_test(is_staff_or_superuser)
def coupon_list(request):
    """List all coupons"""
    coupons = Coupon.objects.all().order_by('-created_at')
    
    # Filtering
    status = request.GET.get('status')
    if status == 'active':
        now = timezone.now()
        coupons = coupons.filter(is_active=True, valid_from__lte=now, valid_to__gte=now)
    elif status == 'expired':
        now = timezone.now()
        coupons = coupons.filter(valid_to__lt=now)
    elif status == 'scheduled':
        now = timezone.now()
        coupons = coupons.filter(valid_from__gt=now)
    
    # Search
    search_query = request.GET.get('q')
    if search_query:
        coupons = coupons.filter(
            Q(code__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(coupons, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_title': 'Coupon Management',
        'page_obj': page_obj,
        'status': status,
        'search_query': search_query or '',
    }
    return render(request, 'admin_dashboard/coupon_list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def coupon_create(request):
    """Create a new coupon"""
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save(commit=False)
            coupon.created_by = request.user
            now = timezone.now()
            coupon.created_at = now
            coupon.updated_at = now
            coupon.save()
            messages.success(request, f'Coupon "{coupon.code}" created successfully!')
            return redirect('admin_dashboard:coupon_list')
    else:
        form = CouponForm()
    
    context = {
        'page_title': 'Create New Coupon',
        'form': form,
    }
    return render(request, 'admin_dashboard/coupon_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def coupon_edit(request, coupon_id):
    """Edit an existing coupon"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            updated_coupon = form.save(commit=False)
            updated_coupon.updated_at = timezone.now()
            updated_coupon.save()
            messages.success(request, f'Coupon "{updated_coupon.code}" updated successfully!')
            return redirect('admin_dashboard:coupon_list')
    else:
        form = CouponForm(instance=coupon)
    
    context = {
        'page_title': f'Edit Coupon: {coupon.code}',
        'form': form,
        'coupon': coupon,
    }
    return render(request, 'admin_dashboard/coupon_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def coupon_toggle_status(request, coupon_id):
    """Toggle coupon active status"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        coupon.is_active = not coupon.is_active
        coupon.save()
        status = 'activated' if coupon.is_active else 'deactivated'
        messages.success(request, f'Coupon "{coupon.code}" {status} successfully!')
    
    return redirect('admin_dashboard:coupon_list')

@login_required
@user_passes_test(is_staff_or_superuser)
def coupon_delete(request, coupon_id):
    """Delete a coupon"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        code = coupon.code
        # Check if coupon is in use
        if AppliedCoupon.objects.filter(coupon=coupon).exists():
            messages.error(request, f"Cannot delete coupon '{code}' as it has been used in orders.")
        else:
            coupon.delete()
            messages.success(request, f"Coupon '{code}' has been deleted successfully.")
        return redirect('admin_dashboard:coupon_list')
    
    # For GET request, show confirmation page
    context = {
        'title': 'Delete Coupon',
        'coupon': coupon,
        'in_use': AppliedCoupon.objects.filter(coupon=coupon).exists()
    }
    return render(request, 'admin_dashboard/coupon_confirm_delete.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def coupon_usage(request, coupon_id):
    """View coupon usage statistics"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    # Get usage statistics using the correct related name 'applications'
    total_usage = coupon.applications.count()
    recent_usage = coupon.applications.select_related('user', 'cart').order_by('-applied_at')[:10]
    
    # Get usage by date (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    usage_by_date = (
        coupon.applications
        .filter(applied_at__gte=thirty_days_ago)
        .extra(select={'date': "date(applied_at)"})
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    context = {
        'page_title': f'Coupon Usage: {coupon.code}',
        'coupon': coupon,
        'total_usage': total_usage,
        'recent_usage': recent_usage,
        'usage_by_date': usage_by_date,
    }
    return render(request, 'admin_dashboard/coupon_usage.html', context)

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code', 'description', 'discount_type', 'discount_value',
            'min_order_amount', 'max_discount', 'valid_from', 'valid_to',
            'usage_limit', 'is_active'
        ]
        widgets = {
            'valid_from': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'onchange': 'handleDateChange(this, "from")',
                    'class': 'datetime-input',
                }
            ),
            'valid_to': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'onchange': 'handleDateChange(this, "to")',
                    'class': 'datetime-input',
                }
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial time to current time
        now = timezone.now()
        current_time = now.strftime('%Y-%m-%dT%H:%M')
        
        # Set initial values for new forms
        if not self.instance.pk:  # Only for new coupons
            self.fields['valid_from'].widget.attrs['value'] = current_time
            self.fields['valid_to'].widget.attrs['value'] = (
                now + timezone.timedelta(days=7)
            ).strftime('%Y-%m-%dT%H:%M')
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        
        if valid_from and valid_to and valid_from >= valid_to:
            raise forms.ValidationError("Valid To date must be after Valid From date.")
            
        # Ensure times are timezone-aware using the configured timezone
        tz = timezone.get_current_timezone()
        if valid_from and valid_from.tzinfo is None:
            cleaned_data['valid_from'] = timezone.make_aware(valid_from, tz)
        if valid_to and valid_to.tzinfo is None:
            cleaned_data['valid_to'] = timezone.make_aware(valid_to, tz)
        
        return cleaned_data
