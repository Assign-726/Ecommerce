from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Q, Count
from django import forms
import pytz

# Set Indian timezone
IST = pytz.timezone('Asia/Kolkata')

from .models import Cart, CartItem, Coupon, AppliedCoupon

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ['product']
    readonly_fields = ['get_total_price']
    
    def get_total_price(self, obj):
        return f'₹{obj.get_total_price()}'
    get_total_price.short_description = 'Total Price'

class AppliedCouponInline(admin.StackedInline):
    model = AppliedCoupon
    extra = 0
    readonly_fields = ['applied_at']
    raw_id_fields = ['coupon', 'user']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'get_total_price']
    list_filter = ['cart__user']
    search_fields = ['product__name', 'cart__user__username']
    raw_id_fields = ['cart', 'product']
    
    def get_total_price(self, obj):
        return f'₹{obj.get_total_price()}'
    get_total_price.short_description = 'Total Price'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'item_count', 'subtotal', 'discount_amount', 'total', 'coupon_info', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'id')
    readonly_fields = ('created_at', 'updated_at', 'subtotal', 'discount_amount', 'total')
    inlines = [CartItemInline, AppliedCouponInline]
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'
    
    def subtotal(self, obj):
        return f'₹{obj.subtotal_price:.2f}'
    subtotal.short_description = 'Subtotal'
    
    def total(self, obj):
        return f'₹{obj.total_price:.2f}'
    total.short_description = 'Total'
    
    def coupon_info(self, obj):
        try:
            applied_coupon = obj.applied_coupon
            return format_html(
                '<span class="text-green-600">{} (-₹{})</span>',
                applied_coupon.coupon.code,
                applied_coupon.discount_amount
            )
        except AppliedCoupon.DoesNotExist:
            return 'No coupon applied'
    coupon_info.short_description = 'Coupon'
    coupon_info.allow_tags = True

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = '__all__'
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        
        if valid_from and valid_to:
            # Make sure times are timezone-aware in UTC
            if valid_from.tzinfo is None:
                valid_from = timezone.make_aware(valid_from, timezone=pytz.utc)
            if valid_to.tzinfo is None:
                valid_to = timezone.make_aware(valid_to, timezone=pytz.utc)
                
            if valid_from >= valid_to:
                raise forms.ValidationError("Valid To date must be after Valid From date.")
            
            # Update the cleaned data with timezone-aware datetimes in UTC
            cleaned_data['valid_from'] = valid_from.astimezone(pytz.utc)
            cleaned_data['valid_to'] = valid_to.astimezone(pytz.utc)
        
        return cleaned_data

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    form = CouponForm
    list_display = ('code', 'description', 'discount_type', 'discount_value', 'is_active', 'times_used', 'usage_limit', 'valid_from', 'valid_to')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code', 'description')
    readonly_fields = ('times_used',)
    list_editable = ('is_active', 'usage_limit')
    readonly_fields = ('times_used', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ['activate_coupons', 'deactivate_coupons']
    fieldsets = (
        ('Coupon Information', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Discount Settings', {
            'fields': ('discount_type', 'discount_value', 'min_order_amount', 'max_discount')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'usage_limit', 'times_used')
        }),
        ('Advanced Options', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            active_count=Count('applications')
        )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('code',)
        return self.readonly_fields

    @admin.action(description='Activate selected coupons')
    def activate_coupons(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} coupon(s) were successfully activated.')

    @admin.action(description='Deactivate selected coupons')
    def deactivate_coupons(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} coupon(s) were successfully deactivated.')

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on first save
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(AppliedCoupon)
class AppliedCouponAdmin(admin.ModelAdmin):
    list_display = ('coupon_code', 'user_email', 'discount_amount', 'applied_at', 'order_reference')
    list_filter = ('applied_at', 'coupon__code')
    search_fields = ('coupon__code', 'user__email', 'user__username', 'cart__order__id')
    readonly_fields = ('applied_at', 'discount_amount')
    raw_id_fields = ('coupon', 'user', 'cart')
    date_hierarchy = 'applied_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('coupon', 'user', 'cart')
    
    def coupon_code(self, obj):
        return obj.coupon.code
    coupon_code.short_description = 'Coupon Code'
    coupon_code.admin_order_field = 'coupon__code'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def order_reference(self, obj):
        if hasattr(obj.cart, 'order') and obj.cart.order:
            return format_html(
                '<a href="{}?id__exact={}">{}</a>',
                reverse('admin:orders_order_changelist'),
                obj.cart.order.id,
                f'Order #{obj.cart.order.id}'
            )
        return 'N/A'
    order_reference.short_description = 'Order'
    order_reference.allow_tags = True
    
    def has_add_permission(self, request):
        return False