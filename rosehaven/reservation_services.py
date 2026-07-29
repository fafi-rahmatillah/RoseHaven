from collections import defaultdict

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from administrator.models import Reservation, ReservationRoom


ACTIVE_RESERVATION_STATUSES = [
    Reservation.Status.WAITING_PAYMENT,
    Reservation.Status.PAID,
    Reservation.Status.CONFIRMED,
    Reservation.Status.CHECKED_IN,
]


@transaction.atomic
def sync_reservation_rooms(reservation, rooms):
    """Simpan seluruh kamar dalam satu reservasi dan hitung ulang totalnya."""
    rooms = list(rooms)
    if not rooms:
        raise ValueError('Minimal pilih satu kamar.')

    reservation.room = rooms[0]
    reservation.save()

    selected_ids = [room.pk for room in rooms]
    reservation.reserved_rooms.exclude(room_id__in=selected_ids).delete()
    for room in rooms:
        ReservationRoom.objects.update_or_create(
            reservation=reservation,
            room=room,
            defaults={'price_per_night': room.price},
        )

    reservation.recalculate_total()
    reservation.ensure_stay_record()
    return reservation


def attach_booked_periods(rooms):
    """Tambahkan atribut booked_periods pada setiap kamar untuk tampilan customer."""
    rooms = list(rooms)
    room_map = {room.pk: room for room in rooms}
    periods = defaultdict(list)
    today = timezone.localdate()

    reservations = (
        Reservation.objects
        .filter(
            Q(room_id__in=room_map) | Q(reserved_rooms__room_id__in=room_map),
            check_out__gte=today,
        )
        .exclude(
            status__in=[
                Reservation.Status.CANCELED,
                Reservation.Status.COMPLETED,
                Reservation.Status.CHECKED_OUT,
            ]
        )
        .prefetch_related('reserved_rooms')
        .distinct()
        .order_by('check_in')
    )

    for reservation in reservations:
        room_ids = set(reservation.reserved_rooms.values_list('room_id', flat=True))
        if not room_ids and reservation.room_id:
            room_ids.add(reservation.room_id)
        for room_id in room_ids:
            if room_id in room_map:
                periods[room_id].append(reservation)

    for room in rooms:
        room.booked_periods = periods.get(room.pk, [])
    return rooms
