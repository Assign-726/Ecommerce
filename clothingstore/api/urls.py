from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from . import views
from .views import (
    CouponListCreateAPIView, 
    CouponDetailAPIView,
    ApplyCouponAPIView, 
    RemoveCouponAPIView, 
    ValidateCouponAPIView
)
from .auth_views import (
    UserRegistrationAPIView,
    UserLoginAPIView,
    UserLogoutAPIView,
    UserProfileAPIView,
    PasswordResetRequestAPIView,
    PasswordResetConfirmAPIView,
)
# Cart APIs removed

app_name = 'api'

urlpatterns = [
    # JWT Token endpoints
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Authentication
    path('auth/register/', UserRegistrationAPIView.as_view(), name='api_register'),
    path('auth/login/', UserLoginAPIView.as_view(), name='api_login'),
    path('auth/logout/', UserLogoutAPIView.as_view(), name='api_logout'),
    path('auth/me/', UserProfileAPIView.as_view(), name='api_profile'),
    path('auth/password-reset/', PasswordResetRequestAPIView.as_view(), name='api_password_reset_request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmAPIView.as_view(), name='api_password_reset_confirm'),
    
    # Product Management
    path('products/', views.ProductListCreateAPIView.as_view(), name='product-list-create'),
    path('products/<slug:slug>/', views.ProductDetailAPIView.as_view(), name='product-detail'),
    path('products/<slug:product_slug>/images/', views.upload_product_images, name='upload-images'),
    path('products/<slug:product_slug>/stock/', views.update_product_stock, name='update-stock'),
    path('images/<int:image_id>/', views.delete_product_image, name='delete-image'),
    
    # Category Management
    path('categories/', views.CategoryListCreateAPIView.as_view(), name='category-list-create'),
    path('categories/<slug:slug>/', views.CategoryDetailAPIView.as_view(), name='category-detail'),
    
    # Order Management
    path('orders/', views.order_list, name='order-list'),
    path('orders/<int:order_id>/status/', views.update_order_status, name='update-order-status'),
    
    # Address Management (user)
    path('addresses/', views.AddressListCreateAPIView.as_view(), name='address-list-create'),
    path('addresses/<int:pk>/', views.AddressDetailAPIView.as_view(), name='address-detail'),
    
    # Analytics
    path('analytics/dashboard/', views.dashboard_stats, name='dashboard-stats'),
    
    # Coupon Management
    path('coupons/', CouponListCreateAPIView.as_view(), name='coupon-list-create'),
    path('coupons/<str:code>/', CouponDetailAPIView.as_view(), name='coupon-detail'),
    path('coupons/apply/', ApplyCouponAPIView.as_view(), name='apply-coupon'),
    path('coupons/remove/', RemoveCouponAPIView.as_view(), name='remove-coupon'),
    path('coupons/validate/', ValidateCouponAPIView.as_view(), name='validate-coupon'),

    # Cart APIs temporarily removed
]
