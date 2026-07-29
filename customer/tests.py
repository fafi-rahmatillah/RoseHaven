from datetime import timedelta
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from io import BytesIO
from administrator.models import Facility, Payment, Reservation, Room, RoomType
from customer.models import CustomerProfile


def image_file(name='proof.jpg'):
    buffer = BytesIO()
    Image.new('RGB', (20, 20), 'white').save(buffer, format='JPEG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


class CustomerFlowTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name='Customer')
        self.user = User.objects.create_user('cust', 'cust@example.com', 'StrongPass123!')
        self.user.groups.add(group)
        CustomerProfile.objects.create(user=self.user, phone='0812', address='Alamat')
        self.room_type = RoomType.objects.create(name='Deluxe', base_price=500000, capacity=2)
        self.room = Room.objects.create(number='101', name='Deluxe 101', room_type=self.room_type)

    def test_registration_creates_customer_group_and_profile(self):
        response = self.client.post(reverse('register'), {
            'name': 'Budi Santoso', 'email': 'budi@example.com', 'phone': '08123',
            'address': 'Bandung', 'password': 'AnotherPass123!', 'password_confirm': 'AnotherPass123!',
        })
        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(email='budi@example.com')
        self.assertTrue(user.groups.filter(name='Customer').exists())
        self.assertEqual(user.customer_profile.phone, '08123')

    def test_reservation_and_payment_upload(self):
        self.client.login(username='cust', password='StrongPass123!')
        check_in = timezone.localdate() + timedelta(days=3)
        check_out = check_in + timedelta(days=2)
        response = self.client.post(reverse('customer:reserve_room', args=[self.room.pk]), {
            'room': self.room.pk, 'check_in': check_in, 'check_out': check_out, 'guests': 2, 'notes': 'Test',
        })
        reservation = Reservation.objects.get(customer=self.user)
        self.assertEqual(reservation.total, 1000000)
        self.assertRedirects(response, reverse('customer:payment_upload', args=[reservation.pk]))
        response = self.client.post(reverse('customer:payment_upload', args=[reservation.pk]), {'proof': image_file()})
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.PAID)
        self.assertEqual(Payment.objects.get(reservation=reservation).status, Payment.Status.PENDING)
        self.assertRedirects(response, reverse('customer:reservation_detail', args=[reservation.pk]))

    def test_overlapping_reservation_rejected(self):
        self.client.login(username='cust', password='StrongPass123!')
        check_in = timezone.localdate() + timedelta(days=5)
        check_out = check_in + timedelta(days=3)
        Reservation.objects.create(customer=self.user, room=self.room, check_in=check_in, check_out=check_out, guests=1)
        response = self.client.post(reverse('customer:reserve_room', args=[self.room.pk]), {
            'room': self.room.pk, 'check_in': check_in + timedelta(days=1),
            'check_out': check_out + timedelta(days=1), 'guests': 1, 'notes': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reservation.objects.count(), 1)
        self.assertContains(response, 'Kamar tidak tersedia')
