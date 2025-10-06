from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
import os

def user_profile_image_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/user_<id>/profile_images/<filename>
    return f'user_{instance.user.id}/profile_images/{filename}'

class UserProfile(models.Model):
    """
    Extends the default User model with additional user profile information
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to=user_profile_image_path, blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
    
    @property
    def profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return '/static/images/default-avatar.png'  # Default avatar path
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

class Address(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ("shipping", "Shipping"),
        ("billing", "Billing"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default="shipping")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Address"
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.full_name} - {self.address_line1}, {self.city}"

    def save(self, *args, **kwargs):
        # Ensure only one default address per user per address_type
        super_should_save_default = self.is_default
        if self.pk is None and super_should_save_default:
            # If creating and set as default, unset others first
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True,
            ).update(is_default=False)
        elif self.pk is not None and super_should_save_default:
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)

        # Sync default shipping address into UserProfile so existing profile views reflect it
        try:
            if hasattr(self.user, "profile"):
                # Determine the user's current default shipping address AFTER this save
                default_shipping = Address.objects.filter(
                    user=self.user, address_type="shipping", is_default=True
                ).order_by("-updated_at", "-created_at").first()

                if default_shipping and default_shipping.pk == self.pk:
                    profile = self.user.profile
                    # Update profile address fields to mirror the default shipping address
                    profile.address_line1 = self.address_line1
                    profile.address_line2 = self.address_line2
                    profile.city = self.city
                    profile.state = self.state
                    profile.postal_code = self.postal_code
                    profile.country = self.country
                    # Keep phone on profile in sync if provided
                    if self.phone_number:
                        profile.phone_number = self.phone_number
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
            # Avoid breaking saves if profile is missing or other issues occur
            pass

# Signal to create/update user profile when User model is created/updated
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()
