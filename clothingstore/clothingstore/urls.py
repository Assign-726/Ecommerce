"""
URL configuration for clothingstore project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('admin_dashboard.urls')),
    path('', include('core.urls')),
    # Redirect /home/ to the root to avoid duplicate 'core' namespace
    path('home/', RedirectView.as_view(url='/', permanent=False)),
    path('products/', include('products.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('accounts/', include('accounts.urls')),
    path('wishlist/', include('wishlist.urls')),
    path('api/', include('api.urls')),
    # Backward-compatible redirect for old reset URL used in emails or env
    # Preserve uid & token query params so the confirm page gets them
    path('reset-password', RedirectView.as_view(url='/accounts/password/reset/confirm', permanent=False, query_string=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)