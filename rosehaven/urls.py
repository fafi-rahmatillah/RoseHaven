from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from customer import views as customer_views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', customer_views.home, name='home'),
    path('tentang/', customer_views.about, name='about'),
    path('kamar/', customer_views.public_rooms, name='public_rooms'),
    path('kamar/<int:pk>/', customer_views.public_room_detail, name='public_room_detail'),
    path('kontak/', customer_views.contact, name='contact'),
    path('login/', customer_views.login_view, name='login'),
    path('registrasi/', customer_views.register_view, name='register'),
    path('logout/', customer_views.logout_view, name='logout'),
    path('arahkan/', customer_views.role_redirect, name='role_redirect'),
    path('administrator/', include('administrator.urls')),
    path('resepsionis/', include('resepsionis.urls')),
    path('customer/', include('customer.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
