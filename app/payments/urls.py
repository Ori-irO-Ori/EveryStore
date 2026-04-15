from django.urls import path
from . import views

urlpatterns = [
    path('create-order/', views.create_paypal_order, name='create_paypal_order'),
    path('capture-order/', views.capture_paypal_order, name='capture_paypal_order'),
    path('return/', views.paypal_return, name='paypal_return'),
]
