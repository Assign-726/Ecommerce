# admin_dashboard/urls.py
from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Dashboard home
    path('', views.dashboard_home, name='dashboard_home'),
    
    # Product management
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='product_delete'),
    path('products/delete-image/', views.delete_product_image, name='delete_product_image'),
    path('products/set-primary-image/', views.set_primary_image, name='set_primary_image'),
    
    # Category management
    path('categories/', views.category_list, name='category_list'),
    
    # Order management
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail_ajax, name='order_detail_ajax'),
    
    # Customer management
    path('customers/', views.customer_list, name='customer_list'),
    
    # Banner management
    path('banners/', views.banner_list, name='banner_list'),
    path('banners/create/', views.banner_create, name='banner_create'),
    path('banners/<int:banner_id>/edit/', views.banner_edit, name='banner_edit'),
    path('banners/<int:banner_id>/delete/', views.banner_delete, name='banner_delete'),
    
    # Coupon management
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.coupon_create, name='coupon_create'),
    path('coupons/<int:coupon_id>/edit/', views.coupon_edit, name='coupon_edit'),
    path('coupons/<int:coupon_id>/toggle-status/', views.coupon_toggle_status, name='coupon_toggle_status'),
    path('coupons/<int:coupon_id>/delete/', views.coupon_delete, name='coupon_delete'),
    path('coupons/<int:coupon_id>/usage/', views.coupon_usage, name='coupon_usage'),
]
