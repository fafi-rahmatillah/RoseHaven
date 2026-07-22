from django.urls import path
from . import views

app_name = 'customer'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profil/', views.profile, name='profile'),
    path('kamar/', views.rooms, name='rooms'),
    path('kamar/<int:pk>/', views.room_detail, name='room_detail'),
    path('reservasi/', views.reserve, name='reserve'),
    path('reservasi/<int:room_id>/', views.reserve, name='reserve_room'),
    path('pembayaran/<int:pk>/', views.payment_upload, name='payment_upload'),
    path('riwayat/', views.history, name='history'),
    path('reservasi/detail/<int:pk>/', views.reservation_detail, name='reservation_detail'),
    path('reservasi/<int:pk>/batalkan/', views.cancel_reservation, name='cancel_reservation'),
]
