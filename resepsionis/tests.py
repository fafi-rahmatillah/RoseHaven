from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administrator.models import (
    Payment,
    Reservation,
    ReservationRoom,
    Room,
    RoomType,
    StayRecord,
)
from customer.models import CustomerProfile
from resepsionis.models import ReceptionistProfile
from rosehaven.reservation_services import sync_reservation_rooms


class ReceptionistFlowTests(TestCase):
    def setUp(self):
        receptionist_group, _ = Group.objects.get_or_create(name='Resepsionis')
        customer_group, _ = Group.objects.get_or_create(name='Customer')

        self.staff = User.objects.create_user('staff', password='StrongPass123!')
        self.staff.groups.add(receptionist_group)
        ReceptionistProfile.objects.create(user=self.staff)

        self.customer = User.objects.create_user('guest', password='StrongPass123!')
        self.customer.groups.add(customer_group)
        self.profile = CustomerProfile.objects.create(
            user=self.customer,
            phone='1',
            address='x',
            nik='3372015201010003',
            identity_status=CustomerProfile.IdentityStatus.VERIFIED,
        )

        room_type = RoomType.objects.create(
            name='Suite',
            base_price=1000000,
            capacity=2,
        )
        self.room = Room.objects.create(
            number='201',
            name='Suite 201',
            room_type=room_type,
        )
        start = timezone.localdate() + timedelta(days=1)
        self.reservation = Reservation.objects.create(
            customer=self.customer,
            room=self.room,
            check_in=start,
            check_out=start + timedelta(days=2),
            status=Reservation.Status.PAID,
        )
        sync_reservation_rooms(self.reservation, [self.room])
        self.payment = Payment.objects.create(
            reservation=self.reservation,
            amount=self.reservation.total,
        )
        stay_record = self.reservation.ensure_stay_record()
        stay_record.ktp_status = StayRecord.KtpStatus.HELD
        stay_record.save(update_fields=['ktp_status'])
        self.client.login(username='staff', password='StrongPass123!')

    def test_checkin_requires_identity_but_reservation_does_not(self):
        self.profile.identity_status = CustomerProfile.IdentityStatus.PENDING
        self.profile.save(update_fields=['identity_status'])
        self.reservation.status = Reservation.Status.CONFIRMED
        self.reservation.save(update_fields=['status'])
        self.payment.status = Payment.Status.VERIFIED
        self.payment.save(update_fields=['status'])

        self.client.post(
            reverse('resepsionis:check_in_action', args=[self.reservation.pk])
        )
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.CONFIRMED)

    def test_verify_checkin_key_return_and_checkout(self):
        self.client.post(
            reverse('resepsionis:verify_payment', args=[self.payment.pk]),
            {'status': Payment.Status.VERIFIED, 'notes': 'OK'},
        )
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.CONFIRMED)

        self.client.post(
            reverse('resepsionis:check_in_action', args=[self.reservation.pk])
        )
        self.reservation.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.CHECKED_IN)
        self.assertEqual(self.room.status, Room.Status.OCCUPIED)

        item = self.reservation.reserved_rooms.get(room=self.room)
        self.client.post(
            reverse('resepsionis:key_return_action', args=[item.pk]),
            {'status': ReservationRoom.KeyStatus.RETURNED, 'notes': 'Baik'},
        )
        item.refresh_from_db()
        self.assertEqual(item.key_status, ReservationRoom.KeyStatus.RETURNED)

        self.client.post(
            reverse('resepsionis:check_out_action', args=[self.reservation.pk])
        )
        self.reservation.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.CHECKED_OUT)
        self.assertEqual(self.room.status, Room.Status.AVAILABLE)
