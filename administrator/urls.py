from django.urls import path
from . import views

app_name = 'administrator'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('kamar/', views.room_list, name='room_list'),
    path('kamar/tambah/', views.room_form, name='room_add'),
    path('kamar/<int:pk>/edit/', views.room_form, name='room_edit'),
    path('kamar/<int:pk>/hapus/', views.room_delete, name='room_delete'),
    path('tipe-kamar/', views.room_type_list, name='room_type_list'),
    path('tipe-kamar/tambah/', views.room_type_form, name='room_type_add'),
    path('tipe-kamar/<int:pk>/edit/', views.room_type_form, name='room_type_edit'),
    path('tipe-kamar/<int:pk>/hapus/', views.room_type_delete, name='room_type_delete'),
    path('fasilitas/', views.facility_list, name='facility_list'),
    path('fasilitas/tambah/', views.facility_form, name='facility_add'),
    path('fasilitas/<int:pk>/edit/', views.facility_form, name='facility_edit'),
    path('fasilitas/<int:pk>/hapus/', views.facility_delete, name='facility_delete'),
    path('customer/', views.customer_list, name='customer_list'),
    path('customer/tambah/', views.customer_form, name='customer_add'),
    path('customer/<int:pk>/edit/', views.customer_form, name='customer_edit'),
    path('customer/<int:pk>/hapus/', views.customer_delete, name='customer_delete'),
    path('reservasi/', views.reservation_list, name='reservation_list'),
    path('reservasi/tambah/', views.reservation_form, name='reservation_add'),
    path('reservasi/<int:pk>/edit/', views.reservation_form, name='reservation_edit'),
    path('reservasi/<int:pk>/hapus/', views.reservation_delete, name='reservation_delete'),
    path('pembayaran/', views.payment_list, name='payment_list'),
    path('pembayaran/<int:pk>/edit/', views.payment_form, name='payment_edit'),
    path('pembayaran/<int:pk>/hapus/', views.payment_delete, name='payment_delete'),
    path('resepsionis/', views.receptionist_list, name='receptionist_list'),
    path('resepsionis/tambah/', views.receptionist_form, name='receptionist_add'),
    path('resepsionis/<int:pk>/edit/', views.receptionist_form, name='receptionist_edit'),
    path('resepsionis/<int:pk>/hapus/', views.receptionist_delete, name='receptionist_delete'),
    path('laporan/', views.reports, name='reports'),
    path('pengaturan/', views.settings_view, name='settings'),
]
