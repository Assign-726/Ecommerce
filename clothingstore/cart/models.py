from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import datetime, timezone as datetime_timezone
from products.models import Product
import uuid

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.username}"
    
    @property
    def total_price(self):
        subtotal = sum(float(item.get_total_price()) for item in self.items.all())
        
        # Check for applied coupon
        try:
            applied_coupon = self.applied_coupon
            if applied_coupon:
                discount = float(applied_coupon.discount_amount)
                total = max(0, subtotal - discount)
                return total
        except AppliedCoupon.DoesNotExist:
            pass
            
        return subtotal
        
    @property
    def subtotal_price(self):
        """Returns the price before any discounts"""
        return sum(item.get_total_price() for item in self.items.all())
        
    @property
    def discount_amount(self):
        """Returns the total discount amount"""
        try:
            return float(self.applied_coupon.discount_amount)
        except (AppliedCoupon.DoesNotExist, AttributeError):
            return 0
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
        
    @property
    def get_total_after_discount(self):
        """
        Returns the total price after applying any discounts.
        This is an alias for total_price for template compatibility.
        """
        return self.total_price

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True)
    color = models.CharField(max_length=20, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'product', 'size', 'color']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def get_total_price(self):
        return self.quantity * self.product.get_price

class Coupon(models.Model):
    PERCENTAGE = 'percentage'
    FIXED = 'fixed'
    
    DISCOUNT_TYPES = [
        (PERCENTAGE, 'Percentage'),
        (FIXED, 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default=PERCENTAGE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField(help_text='Date and time (UTC)')
    valid_to = models.DateTimeField(help_text='Date and time (UTC)')
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=1)
    times_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=False)
    updated_at = models.DateTimeField(auto_now=False)
    
    class Meta:
        ordering = ['-valid_to']
    
    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()}: {self.discount_value})"
        
    def is_valid(self, user=None, cart_total=0, return_reason=True):
        """
        Check if the coupon is currently valid
        
        Args:
            user: Optional user to check usage against
            cart_total: Optional cart total to validate against minimum order amount
            return_reason: If True, returns a tuple of (is_valid, reason)
            
        Returns:
            bool or tuple: If return_reason is False, returns a boolean indicating validity.
                          If return_reason is True, returns a tuple of (is_valid, reason)
        """
        now = timezone.now()
        
        # Ensure valid_from and valid_to are timezone-aware
        try:
            # Get current time in UTC
            now = timezone.now()
            
            # Handle valid_from
            valid_from = self.valid_from
            if valid_from.tzinfo is None:
                valid_from = timezone.make_aware(valid_from, timezone=datetime_timezone.utc)
            valid_from = valid_from.astimezone(datetime_timezone.utc)
            
            # Handle valid_to
            valid_to = self.valid_to
            if valid_to.tzinfo is None:
                valid_to = timezone.make_aware(valid_to, timezone=datetime_timezone.utc)
            valid_to = valid_to.astimezone(datetime_timezone.utc)
            
            # Ensure now is timezone-aware UTC
            if now.tzinfo is None:
                now = timezone.make_aware(now, timezone=datetime_timezone.utc)
            now = now.astimezone(datetime_timezone.utc)
            
        except Exception as e:
            error_msg = f'Invalid coupon date format: {str(e)}'
            return (False, error_msg) if return_reason else False
        
        # Check basic validity
        if not self.is_active:
            return (False, 'This coupon is not active') if return_reason else False
            
        if now < valid_from:
            local_time = valid_from.astimezone().strftime("%b %d, %Y %I:%M %p")
            return (False, f'This coupon is not valid until {local_time}') if return_reason else False
            
        if now > valid_to:
            local_time = valid_to.astimezone().strftime("%b %d, %Y %I:%M %p")
            return (False, f'This coupon expired on {local_time}') if return_reason else False
            
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return (False, 'This coupon has reached its maximum usage limit') if return_reason else False
            
        # Check user-specific usage if user is provided
        if user is not None and user.is_authenticated:
            user_usage = self.applications.filter(user=user).count()
            if self.usage_limit and user_usage >= self.usage_limit:
                return (False, 'You have already used this coupon the maximum number of times') if return_reason else False
        
        # Check minimum order amount if cart_total is provided
        try:
            cart_total = float(cart_total)
            min_amount = float(self.min_order_amount)
            if cart_total > 0 and cart_total < min_amount:
                return (
                    False, 
                    f'Minimum order amount of ₹{min_amount:,.2f} required for this coupon (current: ₹{cart_total:,.2f})'
                ) if return_reason else False
        except (TypeError, ValueError):
            pass
            
        return (True, 'Coupon applied successfully!') if return_reason else True
        
    def calculate_discount(self, amount):
        """
        Calculate the discount amount based on the coupon type and value.
        
        Args:
            amount (float): The base amount to calculate discount from
            
        Returns:
            float: The calculated discount amount
        """
        try:
            amount = float(amount)
            discount_value = float(self.discount_value)
            
            if amount <= 0:
                return 0.0
                
            if self.discount_type == self.PERCENTAGE:
                # Calculate percentage discount
                discount = (discount_value / 100.0) * amount
                
                # Apply max discount if set
                if self.max_discount is not None:
                    max_discount = float(self.max_discount)
                    discount = min(discount, max_discount)
                
                # Ensure discount doesn't exceed order total
                final_discount = min(discount, amount)
                return round(final_discount, 2)
                
            else:  # FIXED discount
                # For fixed amount, just return the value (capped at order total)
                return min(discount_value, amount)
                
        except (TypeError, ValueError) as e:
            print(f"[ERROR] Error calculating discount: {e}")
            return 0.0


class AppliedCoupon(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applied_coupons')
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE, related_name='applied_coupon', null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['coupon', 'user', 'cart']
    
    def __str__(self):
        return f"{self.user.username} - {self.coupon.code}"