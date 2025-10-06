# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView, TemplateView, View
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm
from .models import UserProfile, Address

class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('core:home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def logout_view(request):
    """Custom logout view to handle logout properly"""
    if request.method == 'POST' or request.method == 'GET':
        logout(request)
        messages.success(request, 'You have been logged out successfully!')
        return redirect('core:home')
    return redirect('core:home')

class CustomLogoutView(LogoutView):
    """Custom logout view with proper redirect"""
    next_page = 'core:home'
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully!')
        return super().dispatch(request, *args, **kwargs)

class ProfileView(LoginRequiredMixin, TemplateView):
    """View for displaying user profile"""
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        # Provide addresses to the profile template
        if self.request.user.is_authenticated:
            context['addresses'] = self.request.user.addresses.order_by('-is_default', '-created_at')
        return context

class ProfileEditView(LoginRequiredMixin, UpdateView):
    """View for editing user profile"""
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    
    def get_object(self, queryset=None):
        return self.request.user.profile
    
    def get_success_url(self):
        messages.success(self.request, 'Your profile has been updated successfully!')
        return reverse('accounts:profile')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        return context

@login_required
def delete_profile_picture(request):
    """View to delete user's profile picture"""
    if request.method == 'POST':
        profile = request.user.profile
        if profile.profile_picture:
            profile.profile_picture.delete()
            profile.save()
            messages.success(request, 'Profile picture removed successfully.')
        else:
            messages.info(request, 'No profile picture to remove.')
    return redirect('accounts:profile_edit')


class PasswordResetRequestView(TemplateView):
    """Simple page that posts email to API endpoint /api/auth/password-reset/"""
    template_name = 'accounts/password_reset_request.html'


class PasswordResetConfirmView(TemplateView):
    """Page that allows user to set a new password using uid & token (calls API)."""
    template_name = 'accounts/password_reset_confirm.html'

