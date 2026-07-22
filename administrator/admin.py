from django.contrib import admin
from .models import Facility, RoomType, Room, Reservation, Payment, HotelSetting


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'name', 'room_type', 'price', 'status', 'is_active')
    list_filter = ('status', 'room_type', 'is_active')
    search_fields = ('number', 'name')
    filter_horizontal = ('facilities',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('code', 'customer', 'room', 'check_in', 'check_out', 'status', 'total')
    list_filter = ('status', 'source', 'check_in')
    search_fields = ('code', 'customer__username', 'customer__first_name', 'room__number')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'amount', 'status', 'paid_at', 'verified_by')
    list_filter = ('status',)

admin.site.register(Facility)
admin.site.register(RoomType)
admin.site.register(HotelSetting)
admin.site.site_header = 'RoseHaven Django Administration'
admin.site.site_title = 'RoseHaven'
