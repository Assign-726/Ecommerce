from django.db import models
from django.utils import timezone

# Create your models here.

class Banner(models.Model):
    ANIMATION_CHOICES = [
        ('fade', 'Fade In/Out'),
        ('slide-left', 'Slide from Left'),
        ('slide-right', 'Slide from Right'),
        ('slide-up', 'Slide from Bottom'),
        ('slide-down', 'Slide from Top'),
        ('zoom', 'Zoom In'),
        ('bounce', 'Bounce In'),
    ]
    
    title = models.CharField(max_length=200, help_text="Banner title (e.g., 'New Summer Collection')")
    description = models.TextField(max_length=500, help_text="Banner description or tagline")
    image = models.ImageField(upload_to='banners/', help_text="Banner image (recommended: 1920x600px)")
    
    # Display settings
    is_active = models.BooleanField(default=True, help_text="Show this banner on the website")
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower numbers show first)")
    
    # Animation settings
    animation_type = models.CharField(max_length=20, choices=ANIMATION_CHOICES, default='fade')
    animation_duration = models.PositiveIntegerField(default=3000, help_text="Animation duration in milliseconds")
    
    # Optional link
    link_url = models.URLField(blank=True, null=True, help_text="Optional link when banner is clicked")
    link_text = models.CharField(max_length=50, blank=True, help_text="Button text (e.g., 'Shop Now')")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'
    
    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"
