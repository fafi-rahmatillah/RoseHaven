from django.contrib import admin

from .models import (
    Facility,
    HotelSetting,
    Payment,
    Reservation,
    ReservationRoom,
    Room,
    RoomType,
    StayRecord,
)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'number',
        'name',
        'room_type',
        'price',
        'status',
        'is_active',
    )

    list_filter = (
        'status',
        'room_type',
        'is_active',
    )

    search_fields = (
        'number',
        'name',
    )

    filter_horizontal = (
        'facilities',
    )


class ReservationRoomInline(admin.TabularInline):
    model = ReservationRoom
    extra = 0

    autocomplete_fields = (
        'room',
        'key_given_by',
        'key_returned_by',
    )


class StayRecordInline(admin.StackedInline):
    model = StayRecord
    extra = 0
    max_num = 1
    can_delete = False


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'customer',
        'room',
        'check_in',
        'check_out',
        'status',
        'total',
    )

    list_filter = (
        'status',
        'source',
        'check_in',
    )

    search_fields = (
        'code',
        'customer__username',
        'customer__first_name',
        'room__number',
    )

    inlines = (
        ReservationRoomInline,
        StayRecordInline,
    )


@admin.register(ReservationRoom)
class ReservationRoomAdmin(admin.ModelAdmin):
    list_display = (
        'reservation',
        'room',
        'price_per_night',
        'key_status',
        'key_given_at',
        'key_returned_at',
    )

    list_filter = (
        'key_status',
    )

    search_fields = (
        'reservation__code',
        'room__number',
        'room__name',
    )

    autocomplete_fields = (
        'reservation',
        'room',
        'key_given_by',
        'key_returned_by',
    )


@admin.register(StayRecord)
class StayRecordAdmin(admin.ModelAdmin):
    list_display = (
        'reservation',
        'ktp_status',
        'ktp_received_at',
        'ktp_returned_at',
    )

    list_filter = (
        'ktp_status',
    )

    search_fields = (
        'reservation__code',
        'reservation__customer__username',
    )

    autocomplete_fields = (
        'reservation',
        'ktp_received_by',
        'ktp_returned_by',
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'reservation',
        'amount',
        'status',
        'paid_at',
        'verified_by',
    )

    list_filter = (
        'status',
    )


admin.site.register(Facility)
admin.site.register(RoomType)
admin.site.register(HotelSetting)

admin.site.site_header = 'RoseHaven Django Administration'
admin.site.site_title = 'RoseHaven'