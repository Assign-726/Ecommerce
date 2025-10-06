# products/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms
from django.db import models
from django.forms import TextInput
from .models import Category, Product, ProductImage, Size, ProductSize
from .forms import ProductAdminForm, CategoryAdminForm

class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 1
    fields = ('size', 'quantity')
    verbose_name = 'Size & Quantity'
    verbose_name_plural = 'Sizes & Quantities'
    autocomplete_fields = ['size']
    min_num = 1
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'size':
            # Only show active sizes in the dropdown
            kwargs['queryset'] = Size.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    class Media:
        css = {
            'all': ('admin/css/size-management.css',)
        }
        js = ('admin/js/size-management.js',)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'image_preview')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = "Preview"

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'size_type', 'is_active', 'order', 'product_count')
    list_filter = ('size_type', 'is_active')
    search_fields = ('name', 'display_name')
    list_editable = ('is_active', 'order')
    ordering = ('order', 'name')
    list_per_page = 25
    
    fieldsets = (
        ('Size Information', {
            'fields': ('name', 'display_name', 'size_type')
        }),
        ('Settings', {
            'fields': ('order', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['order'].widget.attrs['style'] = 'width: 50px;'
        return form
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            product_count=models.Count('products')
        )
    
    def product_count(self, obj):
        return obj.product_count
    product_count.admin_order_field = 'product_count'
    product_count.short_description = 'Used In'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Add size type to the options for the select widget
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'size':
            field.label_from_instance = lambda obj: f"{obj.display_name} ({obj.size_type})"
        return field

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ['name', 'slug', 'image_thumbnail', 'product_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description'),
            'description': 'Enter the category name and description. The slug will be auto-generated from the name.'
        }),
        ('Category Image', {
            'fields': ('image', 'image_preview'),
            'description': 'Upload a high-quality image for this category. Recommended size: 800x600px or higher. Supported formats: JPG, PNG, WebP.'
        }),
        ('Status & Settings', {
            'fields': ('is_active',),
            'description': 'Control category visibility and status.'
        }),
    )
    readonly_fields = ('image_preview',)
    
    def image_thumbnail(self, obj):
        """Display small thumbnail in list view"""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.image.url
            )
        return format_html(
            '<div style="width: 50px; height: 50px; background: #f3f4f6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #9ca3af; font-size: 12px;">No Image</div>'
        )
    image_thumbnail.short_description = "Image"
    
    def image_preview(self, obj):
        """Display large preview in edit form"""
        if obj.image:
            return format_html(
                '<div style="margin-bottom: 10px;">'
                '<img src="{}" style="max-width: 300px; max-height: 200px; object-fit: cover; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 2px solid #e5e7eb;" />'
                '<p style="margin-top: 8px; color: #6b7280; font-size: 12px;">'
                '<strong>File:</strong> {} | <strong>Size:</strong> {}x{} pixels'
                '</p>'
                '</div>',
                obj.image.url,
                obj.image.name.split('/')[-1],
                obj.image.width if hasattr(obj.image, 'width') else 'Unknown',
                obj.image.height if hasattr(obj.image, 'height') else 'Unknown'
            )
        return format_html(
            '<div style="padding: 20px; background: #f9fafb; border: 2px dashed #d1d5db; border-radius: 12px; text-align: center; color: #6b7280;">'
            '<svg style="width: 48px; height: 48px; margin: 0 auto 10px; opacity: 0.5;" fill="currentColor" viewBox="0 0 20 20">'
            '<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"></path>'
            '</svg>'
            '<p><strong>No image uploaded</strong></p>'
            '<p style="font-size: 12px; margin-top: 5px;">Upload an image to see preview here</p>'
            '</div>'
        )
    image_preview.short_description = "Image Preview"
    
    def product_count(self, obj):
        count = obj.products.count()
        url = reverse('admin:products_product_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}" style="color: #3b82f6; text-decoration: none; font-weight: 500;">{} products</a>', url, count)
    product_count.short_description = "Products"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ['name', 'category', 'price_display', 'discount_display', 'stock_status', 'available_sizes_list', 'is_active', 'is_featured', 'created_at']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductSizeInline, ProductImageInline]
    list_editable = ['is_active', 'is_featured']
    list_per_page = 20
    ordering = ['-created_at']
    
    def available_sizes_list(self, obj):
        return ", ".join([f"{ps.size.name} ({ps.quantity})" for ps in obj.productsizes.all()])
    available_sizes_list.short_description = 'Available Sizes'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price'),
            'description': 'Set discount_price to enable sale pricing'
        }),
        ('Inventory', {
            'fields': ('stock', 'available_colors'),
            'description': 'Total stock will be calculated from sizes. Enter available colors as a JSON list.'
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
    )
    def price_display(self, obj):
        return "${:.2f}".format(float(obj.price))
    price_display.short_description = "Price"
    price_display.admin_order_field = 'price'
    
    def discount_display(self, obj):
        if obj.discount_price and obj.price > 0:
            savings = obj.price - obj.discount_price
            percentage = (savings / obj.price) * 100
            return format_html(
                '<span style="color: red;">${} ({:.0f}% off)</span>',
                '{:.2f}'.format(float(obj.discount_price)), percentage
            )
        return "-"
    discount_display.short_description = "Sale Price"
    
    def stock_status(self, obj):
        if obj.stock == 0:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.stock < 10:
            return format_html('<span style="color: orange;">Low Stock ({})</span>', obj.stock)
        else:
            return format_html('<span style="color: green;">In Stock ({})</span>', obj.stock)
    stock_status.short_description = "Stock Status"
    stock_status.admin_order_field = 'stock'
    
    actions = ['mark_as_featured', 'mark_as_not_featured', 'mark_as_active', 'mark_as_inactive']
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} products marked as featured.')
    mark_as_featured.short_description = "Mark selected products as featured"
    
    def mark_as_not_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} products removed from featured.')
    mark_as_not_featured.short_description = "Remove selected products from featured"
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products marked as active.')
    mark_as_active.short_description = "Mark selected products as active"
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products marked as inactive.')
    mark_as_inactive.short_description = "Mark selected products as inactive"

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'alt_text', 'is_primary', 'image_preview']
    list_filter = ['is_primary', 'product__category']
    search_fields = ['product__name', 'alt_text']
    list_editable = ['is_primary']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = "Preview"