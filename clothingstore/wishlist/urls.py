from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_view, name='list'),
    path('add/<int:product_id>/', views.add_to_wishlist, name='add'),
    path('remove/<int:product_id>/', views.remove_from_wishlist, name='remove'),
    path('toggle/<int:product_id>/', views.toggle_wishlist, name='toggle'),
    path('clear/', views.clear_wishlist, name='clear'),
]
