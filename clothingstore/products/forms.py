# products/forms.py
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import Product, Category, Size, ProductSize
import os

class ColorCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Custom widget for color selection with visual color swatches"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({'class': 'color-checkbox-widget'})
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        # Color mapping for visual display
        color_map = {
            'black': '#000000',
            'white': '#FFFFFF',
            'red': '#FF0000',
            'blue': '#0000FF',
            'green': '#008000',
            'yellow': '#FFFF00',
            'orange': '#FFA500',
            'purple': '#800080',
            'pink': '#FFC0CB',
            'brown': '#A52A2A',
            'gray': '#808080',
            'navy': '#000080',
            'maroon': '#800000',
            'olive': '#808000',
            'lime': '#00FF00',
            'aqua': '#00FFFF',
            'teal': '#008080',
            'silver': '#C0C0C0',
            'gold': '#FFD700',
            'beige': '#F5F5DC',
        }
        
        hex_color = color_map.get(value, '#CCCCCC')
        border_color = '#000000' if value == 'white' else hex_color
        
        # Add color swatch styling
        option['attrs']['style'] = f'margin-right: 10px;'
        option['label'] = f'<span style="display: inline-block; width: 20px; height: 20px; background-color: {hex_color}; border: 2px solid {border_color}; margin-right: 8px; vertical-align: middle; border-radius: 3px;"></span>{label}'
        
        return option

class ProductAdminForm(forms.ModelForm):
    """Custom form for Product admin with enhanced color selection"""
    
    available_colors = forms.MultipleChoiceField(
        choices=Product.COLOR_CHOICES,
        widget=ColorCheckboxSelectMultiple,
        required=False,
        help_text="Select all available colors for this product"
    )
    
    class Meta:
        model = Product
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for multi-select fields
        if self.instance and self.instance.pk and self.instance.available_colors:
            self.fields['available_colors'].initial = self.instance.available_colors
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Convert multi-select values to lists for JSON storage
        instance.available_colors = self.cleaned_data.get('available_colors', [])
        
        if commit:
            instance.save()
            
            # Handle sizes through the inline formset
            if hasattr(self, 'sizes'):
                self.sizes.save(commit=commit)
                
        return instance

    class Media:
        css = {
            'all': ('admin/css/color-widget.css',)
        }
        js = ('admin/js/color-widget.js',)


class CategoryAdminForm(forms.ModelForm):
    """Custom form for Category admin with enhanced image upload"""
    
    class Meta:
        model = Category
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name (e.g., T-Shirts, Hoodies)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe this category and what products it contains...'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text and styling
        self.fields['name'].help_text = "Enter a unique, descriptive name for this category"
        self.fields['slug'].help_text = "URL-friendly version of the name (auto-generated if left blank)"
        self.fields['description'].help_text = "Provide a detailed description to help customers understand this category"
        self.fields['image'].help_text = (
            "Upload a high-quality category image. "
            "Recommended: 800x600px or higher, JPG/PNG format, max 5MB"
        )
        
        # Make image field more prominent
        self.fields['image'].widget.attrs.update({
            'data-toggle': 'tooltip',
            'data-placement': 'top',
            'title': 'Choose a compelling image that represents this category'
        })
    
    def clean_image(self):
        """Validate uploaded image"""
        image = self.cleaned_data.get('image')
        
        if image:
            # Check file size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError(
                    "Image file too large. Please keep it under 5MB."
                )
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError(
                    f"Unsupported file format. Please use: {', '.join(valid_extensions)}"
                )
            
            # Check image dimensions (minimum requirements)
            try:
                from PIL import Image
                img = Image.open(image)
                width, height = img.size
                
                if width < 400 or height < 300:
                    raise ValidationError(
                        "Image too small. Minimum size: 400x300 pixels. "
                        f"Your image: {width}x{height} pixels."
                    )
                    
                # Reset file pointer for Django to use
                image.seek(0)
                
            except Exception:
                # If PIL is not available, skip dimension check
                pass
        
        return image
    
    def save(self, commit=True):
        """Save category with additional processing"""
        instance = super().save(commit=False)
        
        # Auto-generate slug if not provided
        if not instance.slug and instance.name:
            from django.utils.text import slugify
            instance.slug = slugify(instance.name)
        
        if commit:
            instance.save()
        
        return instance
