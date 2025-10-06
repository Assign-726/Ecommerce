from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=False, null=True) #changes
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('products:list') + f'?category={self.slug}'

class Size(models.Model):
    SIZE_TYPE_CHOICES = [
        ('clothing', 'Clothing'),
        ('shoes', 'Shoes'),
        ('accessories', 'Accessories'),
    ]
    
    # Shoe sizes (US)
    SHOE_SIZES = [
        ('5', 'US 5'), ('5.5', 'US 5.5'),
        ('6', 'US 6'), ('6.5', 'US 6.5'),
        ('7', 'US 7'), ('7.5', 'US 7.5'),
        ('8', 'US 8'), ('8.5', 'US 8.5'),
        ('9', 'US 9'), ('9.5', 'US 9.5'),
        ('10', 'US 10'), ('10.5', 'US 10.5'),
        ('11', 'US 11'), ('11.5', 'US 11.5'),
        ('12', 'US 12'), ('12.5', 'US 12.5'),
        ('13', 'US 13'),
    ]
    
    # Clothing sizes
    CLOTHING_SIZES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
        ('XXXL', 'Triple Extra Large'),
    ]
    
    name = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=50)
    size_type = models.CharField(max_length=20, choices=SIZE_TYPE_CHOICES, default='clothing')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    @classmethod
    def get_available_sizes(cls, size_type):
        """Helper method to get available sizes by type"""
        if size_type == 'shoes':
            return cls.SHOE_SIZES
        return cls.CLOTHING_SIZES
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.display_name

class Product(models.Model):
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
    ]
    
    COLOR_CHOICES = [
        ('black', 'Black'),
        ('white', 'White'),
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('orange', 'Orange'),
        ('purple', 'Purple'),
        ('pink', 'Pink'),
        ('brown', 'Brown'),
        ('gray', 'Gray'),
        ('navy', 'Navy Blue'),
        ('maroon', 'Maroon'),
        ('olive', 'Olive'),
        ('lime', 'Lime'),
        ('aqua', 'Aqua'),
        ('teal', 'Teal'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('beige', 'Beige'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0, help_text="Total stock across all sizes and colors")
    sizes = models.ManyToManyField(Size, through='ProductSize', related_name='products')
    is_active = models.BooleanField(default=True)
    available_colors = models.JSONField(default=list, blank=True, help_text="List of available colors for this product")
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Keep available_sizes for backward compatibility
    @property
    def available_sizes(self):
        """
        Returns a list of size codes (e.g., ["S", "M", "L"]) that are
        available for this product based on related ProductSize entries
        with quantity > 0 and active sizes, ordered by Size.order.
        """
        try:
            # Use select_related to minimize queries and ensure deterministic order
            product_sizes = (
                self.productsizes.select_related('size')
                .filter(quantity__gt=0, size__is_active=True)
                .order_by('size__order', 'size__name')
            )
            return [ps.size.name for ps in product_sizes]
        except Exception:
            # Fallback to empty list if relation not ready (e.g., during migrations)
            return []
    
    @available_sizes.setter
    def available_sizes(self, value):
        # For backward compatibility, but won't actually save to database
        pass
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('products:detail', args=[self.slug])
    
    @property
    def get_price(self):
        return self.discount_price if self.discount_price else self.price
    
    @property
    def has_discount(self):
        return self.discount_price is not None and self.discount_price < self.price

    # ---- Image helpers used across templates (orders list/detail, product cards) ----
    @property
    def primary_image(self):
        """Return the primary ProductImage or the first available image, else None."""
        try:
            img = self.images.filter(is_primary=True).first()
            if img:
                return img
            return self.images.first()
        except Exception:
            return None

    @property
    def get_thumbnail_url(self):
        """
        Safe accessor used in templates. Returns a valid URL to an image to prevent
        broken images in the UI. Order pages rely on this property.
        """
        img = self.primary_image
        if img and getattr(img, 'image', None):
            try:
                return img.image.url
            except Exception:
                pass
        # Fallback placeholder (ensure this exists in static/img)
        placeholder = getattr(settings, 'STATIC_URL', '/static/') + 'img/placeholder-product.svg'
        return placeholder

class ProductSize(models.Model):
    """
    Through model for the many-to-many relationship between Product and Size
    with an additional quantity field
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='productsizes'  # This matches the related_name used in the Product model
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.CASCADE,
        related_name='product_sizes'
    )
    quantity = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('product', 'size')
        verbose_name = 'Product Size'
        verbose_name_plural = 'Product Sizes'
    
    def __str__(self):
        return f"{self.product.name} - {self.size.name} (Qty: {self.quantity})"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Image for {self.product.name}"