from django.urls import path
from django.contrib.auth.views import LogoutView
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password reset (UI calling API)
    path('password/forgot/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset/confirm', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Profile URLs
    path('profile/', login_required(views.ProfileView.as_view()), name='profile'),
    path('profile/edit/', login_required(views.ProfileEditView.as_view()), name='profile_edit'),
    path('profile/picture/delete/', login_required(views.delete_profile_picture), name='delete_profile_picture'),
]

