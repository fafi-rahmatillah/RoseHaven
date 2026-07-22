from django.urls import path
from . import views

app_name = 'resepsionis'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reservasi/', views.reservation_list, name='reservation_list'),
    path('reservasi/tambah/', views.walk_in_add, name='walk_in_add'),
    path('customer/', views.customer_list, name='customer_list'),
    path('kamar/', views.room_list, name='room_list'),
    path('pembayaran/', views.payment_list, name='payment_list'),
    path('pembayaran/<int:pk>/verifikasi/', views.verify_payment, name='verify_payment'),
    path('check-in/', views.check_in_list, name='check_in_list'),
    path('check-in/<int:pk>/', views.check_in_action, name='check_in_action'),
    path('check-out/', views.check_out_list, name='check_out_list'),
    path('check-out/<int:pk>/', views.check_out_action, name='check_out_action'),
    path('jadwal/', views.schedule, name='schedule'),
]
