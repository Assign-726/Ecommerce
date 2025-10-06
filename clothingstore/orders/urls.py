from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('my-orders/', views.order_list, name='list'),
    path('success/<str:order_number>/', views.order_success, name='order_success'),
    path('checkout/', views.checkout, name='checkout'),
    path('verify/razorpay/', views.razorpay_verify, name='razorpay_verify'),
    path('<str:order_number>/', views.order_detail, name='detail'),
    path('<str:order_number>/cancel/', views.cancel_order, name='cancel'),
]