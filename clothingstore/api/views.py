# api/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from products.models import Product, Category, ProductImage
from orders.models import Order
from accounts.models import Address
from .serializers import (
    ProductSerializer, 
    ProductCreateUpdateSerializer,
    CategorySerializer,
    ProductImageSerializer,
    AddressSerializer
)
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from django.utils import timezone
from cart.models import Coupon, AppliedCoupon, Cart
from .serializers import (
    CouponSerializer, 
    ApplyCouponSerializer, 
    AppliedCouponSerializer
)
# Cart APIs temporarily removed; corresponding imports cleaned up

# Product Management APIs
class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductSerializer
    
    def get_queryset(self):
        queryset = Product.objects.all()
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset

class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductSerializer

# Category Management APIs
class CategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'slug'

# Product Image Management
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def upload_product_images(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    
    uploaded_files = request.FILES.getlist('images')
    created_images = []
    
    for uploaded_file in uploaded_files:
        image = ProductImage.objects.create(
            product=product,
            image=uploaded_file,
            alt_text=request.data.get('alt_text', product.name)
        )
        created_images.append(image)
    
    serializer = ProductImageSerializer(created_images, many=True)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_product_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

# Inventory Management
@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def update_product_stock(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    new_stock = request.data.get('stock')
    
    if new_stock is not None:
        product.stock = new_stock
        product.save()
        
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    
    return Response(
        {'error': 'Stock value is required'}, 
        status=status.HTTP_400_BAD_REQUEST
    )

def _sync_default_shipping_profile(user):
    """Mirror the user's default shipping address into their UserProfile."""
    try:
        default_shipping = Address.objects.filter(
            user=user, address_type="shipping", is_default=True
        ).order_by("-updated_at", "-created_at").first()
        if default_shipping and hasattr(user, "profile"):
            profile = user.profile
            profile.address_line1 = default_shipping.address_line1
            profile.address_line2 = default_shipping.address_line2
            profile.city = default_shipping.city
            profile.state = default_shipping.state
            profile.postal_code = default_shipping.postal_code
            profile.country = default_shipping.country
            if default_shipping.phone_number:
                profile.phone_number = default_shipping.phone_number
            profile.save(update_fields=[
                "address_line1",
                "address_line2",
                "city",
                "state",
                "postal_code",
                "country",
                "phone_number",
            ])
    except Exception:
        # Do not break the API if syncing fails
        pass

# Address Management APIs (user scoped)
class AddressListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        # After create, if this is default shipping, mirror to profile
        _sync_default_shipping_profile(self.request.user)

class AddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Ensure users can only access their own addresses
        return Address.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        # After update, ensure profile reflects current default shipping
        _sync_default_shipping_profile(self.request.user)

    def perform_destroy(self, instance):
        user = self.request.user
        super().perform_destroy(instance)
        # After delete, ensure profile reflects current default shipping (might have changed)
        _sync_default_shipping_profile(user)

# Order Management APIs
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.query_params.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    data = []
    for order in orders:
        data.append({
            'id': order.id,
            'order_number': order.order_number,
            'user': order.user.username,
            'status': order.status,
            'total_amount': str(order.total_amount),
            'created_at': order.created_at,
            'items_count': order.items.count(),
        })
    
    return Response(data)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.data.get('status')
    
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save()
        
        return Response({
            'order_number': order.order_number,
            'status': order.status,
            'message': f'Order status updated to {new_status}'
        })
    
    return Response(
        {'error': 'Invalid status'}, 
        status=status.HTTP_400_BAD_REQUEST
    )

# Analytics APIs
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def dashboard_stats(request):
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    
    # Get stats for the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    stats = {
        'total_products': Product.objects.filter(is_active=True).count(),
        'total_orders': Order.objects.count(),
        'total_revenue': Order.objects.filter(
            payment_status='completed'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'recent_orders': Order.objects.filter(
            created_at__gte=thirty_days_ago
        ).count(),
        'low_stock_products': Product.objects.filter(
            is_active=True, stock__lt=10
        ).count(),
    }
    
    return Response(stats)


 

# Coupon Management APIs
class CouponListCreateAPIView(generics.ListCreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CouponDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'code'
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ApplyCouponAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ApplyCouponSerializer
    
    def post(self, request, *args, **kwargs):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return Response(
                {"error": "No active cart found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        coupon = serializer.validated_data['code']
        discount_amount = coupon.calculate_discount(cart.total_price)
        
        # Remove any existing applied coupon
        AppliedCoupon.objects.filter(cart=cart).delete()
        
        # Apply new coupon
        applied_coupon = AppliedCoupon.objects.create(
            coupon=coupon,
            user=request.user,
            cart=cart,
            discount_amount=discount_amount
        )
        
        # Update coupon usage
        coupon.times_used += 1
        coupon.save()
        
        return Response({
            "message": "Coupon applied successfully",
            "discount_amount": str(discount_amount),
            "coupon": CouponSerializer(coupon, context={'request': request}).data
        })


class RemoveCouponAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, *args, **kwargs):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return Response(
                {"error": "No active cart found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            applied_coupon = AppliedCoupon.objects.get(cart=cart)
            coupon = applied_coupon.coupon
            
            # Update coupon usage
            coupon.times_used = max(0, coupon.times_used - 1)
            coupon.save()
            
            # Remove the applied coupon
            applied_coupon.delete()
            
            return Response({"message": "Coupon removed successfully"})
            
        except AppliedCoupon.DoesNotExist:
            return Response(
                {"error": "No coupon applied to this cart"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class ValidateCouponAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ApplyCouponSerializer
    
    def post(self, request, *args, **kwargs):
        cart = Cart.objects.filter(user=request.user).first()
        cart_total = cart.total_price if cart else 0
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        coupon = serializer.validated_data['code']
        is_valid, message = coupon.is_valid(request.user, cart_total)
        
        if not is_valid:
            return Response(
                {"valid": False, "message": message},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        discount_amount = coupon.calculate_discount(cart_total)
        
        return Response({
            "valid": True,
            "message": "Coupon is valid",
            "coupon": CouponSerializer(
                coupon, 
                context={
                    'request': request,
                    'cart_total': cart_total
                }
            ).data,
            "discount_amount": str(discount_amount)
        })
