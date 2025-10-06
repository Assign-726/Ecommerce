from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse

from .models import Coupon, AppliedCoupon, Cart

class ApplyCouponForm(forms.Form):
    coupon = forms.ModelChoiceField(
        queryset=Coupon.objects.filter(is_active=True),
        label="Select Coupon",
        required=True
    )

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code', 'description', 'discount_type', 'discount_value',
            'min_order_amount', 'max_discount', 'valid_from', 'valid_to',
            'is_active', 'usage_limit'
        ]
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        
        if valid_from and valid_to and valid_from >= valid_to:
            raise forms.ValidationError("Valid To date must be after Valid From date.")
        
        return cleaned_data

class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'valid_from', 'valid_to', 'times_used', 'usage_limit')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code', 'description')
    readonly_fields = ('times_used', 'created_at', 'updated_at')
    list_editable = ('is_active',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'add-coupon/',
                self.admin_site.admin_view(self.add_coupon_view),
                name='add-coupon',
            ),
            path(
                'apply-coupon/',
                self.admin_site.admin_view(self.apply_coupon_view),
                name='apply-coupon',
            ),
        ]
        return custom_urls + urls
    
    def add_coupon_view(self, request):
        if request.method == 'POST':
            form = CouponForm(request.POST)
            if form.is_valid():
                coupon = form.save(commit=False)
                coupon.code = coupon.code.upper()  # Ensure code is uppercase
                coupon.save()
                self.message_user(request, f'Successfully created coupon {coupon.code}')
                return redirect('admin:cart_coupon_changelist')
        else:
            form = CouponForm(initial={
                'is_active': True,
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timezone.timedelta(days=30),
                'usage_limit': 100
            })
        
        context = self.admin_site.each_context(request)
        context.update({
            'opts': self.model._meta,
            'form': form,
            'title': 'Add New Coupon',
            'has_permission': True,
            'is_popup': False,
        })
        return TemplateResponse(request, 'admin/cart/add_coupon.html', context)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'apply-coupon/',
                self.admin_site.admin_view(self.apply_coupon_view),
                name='apply-coupon',
            ),
        ]
        return custom_urls + urls
    
    def apply_coupon_view(self, request):
        if request.method == 'POST':
            form = ApplyCouponForm(request.POST)
            if form.is_valid():
                coupon = form.cleaned_data['coupon']
                cart_id = request.GET.get('cart_id')
                try:
                    cart = Cart.objects.get(id=cart_id)
                    # Remove any existing coupon
                    AppliedCoupon.objects.filter(cart=cart).delete()
                    # Apply new coupon
                    discount = coupon.calculate_discount(cart.subtotal_price)
                    AppliedCoupon.objects.create(
                        coupon=coupon,
                        user=cart.user,
                        cart=cart,
                        discount_amount=discount
                    )
                    coupon.times_used += 1
                    coupon.save()
                    self.message_user(request, f'Successfully applied coupon {coupon.code} to cart #{cart.id}')
                except Cart.DoesNotExist:
                    self.message_user(request, 'Cart not found', level=messages.ERROR)
                return redirect('admin:cart_cart_changelist')
        else:
            form = ApplyCouponForm()
        
        context = self.admin_site.each_context(request)
        context.update({
            'opts': self.model._meta,
            'form': form,
            'title': 'Apply Coupon to Cart',
        })
        return TemplateResponse(request, 'admin/cart/apply_coupon.html', context)

class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'item_count', 'subtotal', 'discount_amount', 'total', 'coupon_info', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'id')
    readonly_fields = ('created_at', 'updated_at', 'subtotal', 'discount_amount', 'total')
    
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
                '<span class="text-green-600">{} (-₹{})</span> <a href="{}?id={}" class="button">Change</a>',
                applied_coupon.coupon.code,
                applied_coupon.discount_amount,
                reverse('admin:apply-coupon'),
                obj.id
            )
        except AppliedCoupon.DoesNotExist:
            return format_html(
                '<a href="{}?cart_id={}" class="button">Apply Coupon</a>',
                reverse('admin:apply-coupon'),
                obj.id
            )
    coupon_info.short_description = 'Coupon'
    coupon_info.allow_tags = True
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'apply-coupon/',
                self.admin_site.admin_view(CouponAdmin(self.model, self.admin_site).apply_coupon_view),
                name='apply-coupon',
            ),
        ]
        return custom_urls + urls
