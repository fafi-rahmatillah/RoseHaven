from django.urls import path
from . import views

app_name = 'resepsionis'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reservasi/', views.reservation_list, name='reservation_list'),
    path('reservasi/tambah/', views.walk_in_add, name='walk_in_add'),
    path('reservasi/<int:pk>/', views.reservation_detail, name='reservation_detail'),
    path('customer/', views.customer_list, name='customer_list'),
    path('validasi-identitas/', views.identity_list, name='identity_list'),
    path('validasi-identitas/<int:pk>/', views.identity_detail, name='identity_detail'),
    path('validasi-identitas/<int:pk>/proses/', views.validate_identity, name='validate_identity'),
    path('jaminan-ktp/', views.ktp_guarantee_list, name='ktp_guarantee_list'),
    path('jaminan-ktp/<int:pk>/terima/', views.receive_ktp, name='receive_ktp'),
    path('jaminan-ktp/<int:pk>/kembalikan/', views.return_ktp, name='return_ktp'),
    path('kamar/', views.room_list, name='room_list'),
    path('pembayaran/', views.payment_list, name='payment_list'),
    path('pembayaran/<int:pk>/verifikasi/', views.verify_payment, name='verify_payment'),
    path('check-in/', views.check_in_list, name='check_in_list'),
    path('check-in/<int:pk>/', views.check_in_action, name='check_in_action'),
    path('check-out/', views.check_out_list, name='check_out_list'),
    path('check-out/<int:pk>/', views.check_out_action, name='check_out_action'),
    path('kunci/<int:item_pk>/kembali/', views.key_return_action, name='key_return_action'),
    path('jadwal/', views.schedule, name='schedule'),
]
