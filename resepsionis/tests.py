from datetime import timedelta
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from administrator.models import Payment, Reservation, Room, RoomType
from customer.models import CustomerProfile
from resepsionis.models import ReceptionistProfile


class ReceptionistFlowTests(TestCase):
    def setUp(self):
        rg, _ = Group.objects.get_or_create(name='Resepsionis')
        cg, _ = Group.objects.get_or_create(name='Customer')
        self.staff = User.objects.create_user('staff', password='StrongPass123!')
        self.staff.groups.add(rg)
        ReceptionistProfile.objects.create(user=self.staff)
        self.customer = User.objects.create_user('guest', password='StrongPass123!')
        self.customer.groups.add(cg)
        CustomerProfile.objects.create(user=self.customer, phone='1', address='x')
        rt = RoomType.objects.create(name='Suite', base_price=1000000, capacity=2)
        self.room = Room.objects.create(number='201', name='Suite 201', room_type=rt)
        start = timezone.localdate() + timedelta(days=1)
        self.reservation = Reservation.objects.create(customer=self.customer, room=self.room, check_in=start, check_out=start + timedelta(days=2), status=Reservation.Status.PAID)
        self.payment = Payment.objects.create(reservation=self.reservation, amount=self.reservation.total)
        self.client.login(username='staff', password='StrongPass123!')

    def test_verify_checkin_checkout(self):
        self.client.post(reverse('resepsionis:verify_payment', args=[self.payment.pk]), {'status': Payment.Status.VERIFIED, 'notes': 'OK'})
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.CONFIRMED)
        self.client.post(reverse('resepsionis:check_in_action', args=[self.reservation.pk]))
        self.reservation.refresh_from_db(); self.room.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.CHECKED_IN)
        self.assertEqual(self.room.status, Room.Status.OCCUPIED)
        self.client.post(reverse('resepsionis:check_out_action', args=[self.reservation.pk]))
        self.reservation.refresh_from_db(); self.room.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.CHECKED_OUT)
        self.assertEqual(self.room.status, Room.Status.AVAILABLE)

