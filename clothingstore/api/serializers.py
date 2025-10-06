# api/serializers.py
from datetime import datetime
from django.utils import timezone
from rest_framework import serializers
from products.models import Product, Category, ProductImage
from accounts.models import Address
from orders.models import Cart, CartItem
from cart.models import Coupon, AppliedCoupon



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'
    
    def create(self, validated_data):
        return Product.objects.create(**validated_data)

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ['created_at', 'updated_at']

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        # user is set from request, not writable from client
        read_only_fields = ["id", "user", "created_at", "updated_at"]
        fields = [
            "id",
            "full_name",
            "phone_number",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "address_type",
            "is_default",
            "created_at",
            "updated_at",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_price', 'image', 'quantity', 'total_price']

    def get_product_price(self, obj):
        # Prefer discounted price if available via Product.get_price
        return str(obj.product.get_price)

    def get_image(self, obj):
        # Return primary product image or first image path if available
        primary = obj.product.images.filter(is_primary=True).first()
        if primary and primary.image:
            return primary.image.url
        first = obj.product.images.first()
        return first.image.url if first and first.image else None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    coupon = serializers.CharField(source='applied_coupon.coupon.code', read_only=True)
    shipping_address = serializers.SerializerMethodField()
    payment_details = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'total_items', 'created_at', 'updated_at', 'applied_coupon']

    def get_total_price(self, obj):
        # Ensure we return stringified decimal similar to example
        return str(obj.total_price)

    def get_shipping_address(self, obj):
        # Prefer default shipping address; fallback to any address
        address = Address.objects.filter(user=obj.user, address_type="shipping", is_default=True).order_by('-updated_at', '-created_at').first()
        if not address:
            address = Address.objects.filter(user=obj.user).order_by('-is_default', '-updated_at', '-created_at').first()
        if not address:
            return None
        cart = self.context.get('cart')
        return {
            "id": address.id,
            "street": address.address_line1,
            "city": address.city,
            "state": address.state,
            "zip_code": address.postal_code,
            "country": address.country,
            'total_price': cart.total_price,
            'total_items': cart.total_items,
            'applied_coupon': cart.applied_coupon.discount_amount if hasattr(cart, 'applied_coupon') and cart.applied_coupon else None,
        }

    def get_payment_details(self, obj):
        # Implement payment details logic here
        return {}


class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()
    validation_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_value',
            'min_order_amount', 'max_discount', 'valid_from', 'valid_to',
            'usage_limit', 'times_used', 'is_active', 'is_valid', 'validation_message'
        ]
        read_only_fields = ['id', 'times_used', 'is_valid', 'validation_message']
    
    def get_is_valid(self, obj):
        request = self.context.get('request')
        cart_total = self.context.get('cart_total', 0)
        if request and request.user.is_authenticated:
            is_valid, _ = obj.is_valid(user=request.user, cart_total=cart_total)
            return is_valid
        return obj.is_active and obj.valid_from <= timezone.now() <= obj.valid_to
    
    def get_validation_message(self, obj):
        request = self.context.get('request')
        cart_total = self.context.get('cart_total', 0)
        if request and request.user.is_authenticated:
            _, message = obj.is_valid(user=request.user, cart_total=cart_total)
            return message
        return ""


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50, required=True)
    
    def validate_code(self, value):
        try:
            coupon = Coupon.objects.get(code=value.upper(), is_active=True)
            return coupon
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code")
    
    def validate(self, data):
        request = self.context.get('request')
        cart = self.context.get('cart')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        if not cart:
            raise serializers.ValidationError("No cart found")
            
        coupon = data['code']
        is_valid, message = coupon.is_valid(request.user, cart.total_price)
        
        if not is_valid:
            raise serializers.ValidationError({"code": message})
            
        return {"coupon": coupon, "cart": cart}


class AppliedCouponSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source='coupon.code')
    discount_type = serializers.CharField(source='coupon.discount_type')
    discount_value = serializers.DecimalField(source='coupon.discount_value', max_digits=10, decimal_places=2)
    
    class Meta:
        model = AppliedCoupon
        fields = ['code', 'discount_type', 'discount_value', 'discount_amount', 'applied_at']
