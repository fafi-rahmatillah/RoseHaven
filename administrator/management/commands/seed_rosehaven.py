from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from administrator.models import Facility, HotelSetting, Payment, Reservation, Room, RoomType
from customer.models import CustomerProfile
from resepsionis.models import ReceptionistProfile
from rosehaven.reservation_services import sync_reservation_rooms


class Command(BaseCommand):
    help = 'Membuat data awal dan akun demo RoseHaven.'

    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name='Administrator')
        receptionist_group, _ = Group.objects.get_or_create(name='Resepsionis')
        customer_group, _ = Group.objects.get_or_create(name='Customer')

        admin, _ = User.objects.get_or_create(username='administrator')
        admin.first_name = 'Admin'
        admin.last_name = 'RoseHaven'
        admin.email = 'admin@rosehaven.test'
        admin.is_staff = admin.is_superuser = admin.is_active = True
        admin.set_password('RoseHaven123!')
        admin.save()
        admin.groups.clear()
        admin.groups.add(admin_group)

        receptionist, _ = User.objects.get_or_create(username='resepsionis')
        receptionist.first_name = 'Rina'
        receptionist.last_name = 'Resepsionis'
        receptionist.email = 'resepsionis@rosehaven.test'
        receptionist.is_active = True
        receptionist.set_password('RoseHaven123!')
        receptionist.save()
        receptionist.groups.clear()
        receptionist.groups.add(receptionist_group)
        ReceptionistProfile.objects.update_or_create(
            user=receptionist,
            defaults={'phone': '081234567891', 'shift': 'MORNING', 'is_active': True},
        )

        customer, _ = User.objects.get_or_create(username='customer')
        customer.first_name = 'Citra'
        customer.last_name = 'Customer'
        customer.email = 'customer@rosehaven.test'
        customer.is_active = True
        customer.set_password('RoseHaven123!')
        customer.save()
        customer.groups.clear()
        customer.groups.add(customer_group)
        CustomerProfile.objects.update_or_create(
            user=customer,
            defaults={
                'phone': '081234567892',
                'address': 'Jl. Melati No. 12, Indonesia',
                'nik': '3372015201010001',
                'is_married': False,
                'identity_status': CustomerProfile.IdentityStatus.PENDING,
            },
        )

        HotelSetting.objects.update_or_create(
            pk=1,
            defaults={
                'name': 'RoseHaven Hotel',
                'tagline': 'A timeless stay, wrapped in comfort.',
                'description': (
                    'RoseHaven adalah hotel bintang 4 yang memadukan suasana elegan, '
                    'kenyamanan modern, dan pelayanan hangat.'
                ),
                'address': 'Jl. Mawar Indah No. 8, Indonesia',
                'phone': '+62 812-3456-7890',
                'email': 'hello@rosehaven.test',
                'bank_name': 'Bank RoseHaven',
                'bank_account': '1234567890',
                'bank_holder': 'RoseHaven Hotel',
            },
        )

        facility_data = [
            ('Wi-Fi Cepat', '⌁', 'Akses internet di seluruh kamar'),
            ('Smart TV', '▣', 'Layanan hiburan digital'),
            ('AC', '❄', 'Pendingin ruangan'),
            ('Sarapan', '☕', 'Sarapan untuk tamu'),
            ('Bathtub', '♨', 'Bathtub air hangat'),
            ('Mini Bar', '◇', 'Minuman dan makanan ringan'),
            ('Balkon', '⌂', 'Balkon pribadi'),
            ('Brankas', '▧', 'Penyimpanan barang berharga'),
        ]
        facilities = {}
        for name, icon, description in facility_data:
            facilities[name], _ = Facility.objects.update_or_create(
                name=name,
                defaults={'icon': icon, 'description': description},
            )

        deluxe, _ = RoomType.objects.update_or_create(
            name='Deluxe',
            defaults={
                'description': 'Kamar elegan untuk dua tamu dengan fasilitas lengkap.',
                'base_price': Decimal('850000'),
                'capacity': 2,
                'bed_type': 'King Bed',
                'size_m2': 30,
            },
        )
        executive, _ = RoomType.objects.update_or_create(
            name='Executive',
            defaults={
                'description': 'Ruang lebih luas untuk perjalanan bisnis atau liburan.',
                'base_price': Decimal('1250000'),
                'capacity': 3,
                'bed_type': 'King Bed + Sofa',
                'size_m2': 42,
            },
        )
        suite, _ = RoomType.objects.update_or_create(
            name='Rose Suite',
            defaults={
                'description': 'Suite mewah dengan area duduk dan balkon pribadi.',
                'base_price': Decimal('1950000'),
                'capacity': 4,
                'bed_type': 'Super King Bed',
                'size_m2': 60,
            },
        )

        room_specs = [
            ('101', 'Deluxe Rose', deluxe, 'rooms/room-101.jpg', ['Wi-Fi Cepat', 'Smart TV', 'AC', 'Sarapan']),
            ('102', 'Deluxe Garden', deluxe, 'rooms/room-102.jpg', ['Wi-Fi Cepat', 'Smart TV', 'AC', 'Brankas']),
            ('201', 'Executive Haven', executive, 'rooms/room-201.jpg', ['Wi-Fi Cepat', 'Smart TV', 'AC', 'Mini Bar', 'Sarapan']),
            ('202', 'Executive Burgundy', executive, 'rooms/room-202.jpg', ['Wi-Fi Cepat', 'Smart TV', 'AC', 'Bathtub', 'Brankas']),
            ('301', 'Rose Suite Gold', suite, 'rooms/room-301.jpg', ['Wi-Fi Cepat', 'Smart TV', 'AC', 'Bathtub', 'Mini Bar', 'Balkon', 'Sarapan']),
            ('302', 'Rose Suite Royal', suite, 'rooms/room-302.jpg', ['Wi-Fi Cepat', 'Smart TV', 'AC', 'Bathtub', 'Mini Bar', 'Balkon', 'Brankas']),
        ]
        rooms = []
        for number, name, room_type, image, facility_names in room_specs:
            room, _ = Room.objects.update_or_create(
                number=number,
                defaults={
                    'name': name,
                    'room_type': room_type,
                    'description': room_type.description,
                    'status': Room.Status.AVAILABLE,
                    'image': image,
                    'is_active': True,
                },
            )
            room.facilities.set([facilities[item] for item in facility_names])
            rooms.append(room)

        today = timezone.localdate()
        future, _ = Reservation.objects.get_or_create(
            customer=customer,
            room=rooms[0],
            check_in=today + timedelta(days=7),
            check_out=today + timedelta(days=10),
            defaults={
                'guests': 3,
                'notes': 'Contoh satu reservasi dengan dua kamar.',
                'status': Reservation.Status.WAITING_PAYMENT,
                'source': Reservation.Source.ONLINE,
                'created_by': customer,
            },
        )
        sync_reservation_rooms(future, [rooms[0], rooms[1]])

        confirmed, _ = Reservation.objects.get_or_create(
            customer=customer,
            room=rooms[2],
            check_in=today + timedelta(days=14),
            check_out=today + timedelta(days=16),
            defaults={
                'guests': 2,
                'status': Reservation.Status.CONFIRMED,
                'source': Reservation.Source.ONLINE,
                'created_by': customer,
            },
        )
        sync_reservation_rooms(confirmed, [rooms[2]])
        Payment.objects.update_or_create(
            reservation=confirmed,
            defaults={
                'amount': confirmed.total,
                'status': Payment.Status.VERIFIED,
                'verified_by': receptionist,
                'verified_at': timezone.now(),
                'notes': 'Pembayaran demo terverifikasi.',
            },
        )

        self.stdout.write(self.style.SUCCESS('Data RoseHaven berhasil dibuat.'))
        self.stdout.write('Akun demo: administrator / resepsionis / customer')
        self.stdout.write('Password semua akun: RoseHaven123!')
