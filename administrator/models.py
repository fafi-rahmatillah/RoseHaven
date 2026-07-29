import secrets
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Facility(models.Model):
    name = models.CharField('Nama fasilitas', max_length=100, unique=True)
    icon = models.CharField('Ikon/emoji', max_length=20, blank=True, default='✦')
    description = models.CharField('Keterangan', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Fasilitas'
        verbose_name_plural = 'Fasilitas'
        ordering = ['name']

    def __str__(self):
        return self.name


class RoomType(models.Model):
    name = models.CharField('Nama tipe', max_length=100, unique=True)
    description = models.TextField('Deskripsi', blank=True)
    base_price = models.DecimalField('Harga dasar per malam', max_digits=12, decimal_places=2)
    capacity = models.PositiveSmallIntegerField('Kapasitas', default=2)
    bed_type = models.CharField('Jenis tempat tidur', max_length=100, default='Queen Bed')
    size_m2 = models.PositiveSmallIntegerField('Luas kamar (m²)', default=24)

    class Meta:
        verbose_name = 'Tipe kamar'
        verbose_name_plural = 'Tipe kamar'
        ordering = ['base_price']
        constraints = [
            models.CheckConstraint(condition=Q(base_price__gte=0), name='roomtype_price_gte_0'),
            models.CheckConstraint(condition=Q(capacity__gte=1), name='roomtype_capacity_gte_1'),
            models.CheckConstraint(condition=Q(size_m2__gte=1), name='roomtype_size_gte_1'),
        ]

    def __str__(self):
        return self.name


class Room(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Tersedia'
        OCCUPIED = 'OCCUPIED', 'Terisi'
        MAINTENANCE = 'MAINTENANCE', 'Perawatan'

    number = models.CharField('Nomor kamar', max_length=20, unique=True)
    name = models.CharField('Nama kamar', max_length=120)
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT,
        related_name='rooms',
        verbose_name='Tipe',
    )
    custom_price = models.DecimalField(
        'Harga khusus',
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    description = models.TextField('Deskripsi', blank=True)
    facilities = models.ManyToManyField(
        Facility,
        blank=True,
        related_name='rooms',
        verbose_name='Fasilitas',
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    image = models.ImageField('Foto kamar', upload_to='rooms/', blank=True)
    is_active = models.BooleanField('Aktif', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kamar'
        verbose_name_plural = 'Kamar'
        ordering = ['number']
        indexes = [
            models.Index(fields=['status', 'is_active'], name='room_status_active_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(custom_price__isnull=True) | Q(custom_price__gte=0),
                name='room_custom_price_gte_0',
            ),
        ]

    @property
    def price(self):
        return self.custom_price if self.custom_price is not None else self.room_type.base_price

    def is_available(self, check_in=None, check_out=None, exclude_reservation=None):
        """Ketersediaan dihitung untuk kamar ini, bukan hanya berdasarkan tipe kamar."""
        if not self.is_active or self.status == self.Status.MAINTENANCE:
            return False

        if not check_in or not check_out:
            return self.status == self.Status.AVAILABLE

        reservations = Reservation.objects.filter(
            Q(room=self) | Q(reserved_rooms__room=self)
        ).exclude(
            status__in=[
                Reservation.Status.CANCELED,
                Reservation.Status.COMPLETED,
                Reservation.Status.CHECKED_OUT,
            ]
        ).distinct()

        if exclude_reservation:
            reservations = reservations.exclude(pk=exclude_reservation)

        return not reservations.filter(
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).exists()

    def __str__(self):
        return f'{self.number} - {self.name}'


class Reservation(models.Model):
    class Status(models.TextChoices):
        WAITING_PAYMENT = 'WAITING_PAYMENT', 'Menunggu Pembayaran'
        PAID = 'PAID', 'Sudah Dibayar'
        CONFIRMED = 'CONFIRMED', 'Dikonfirmasi'
        CHECKED_IN = 'CHECKED_IN', 'Check In'
        CHECKED_OUT = 'CHECKED_OUT', 'Check Out'
        COMPLETED = 'COMPLETED', 'Selesai'
        CANCELED = 'CANCELED', 'Dibatalkan'

    class Source(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        WALK_IN = 'WALK_IN', 'Datang Langsung'

    code = models.CharField('Kode reservasi', max_length=24, unique=True, editable=False)
    customer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='hotel_reservations',
        verbose_name='Customer',
    )
    # Kamar utama dipertahankan untuk kompatibilitas data lama. Seluruh kamar
    # dalam reservasi dicatat pada ReservationRoom.
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name='Kamar utama',
    )
    check_in = models.DateField('Tanggal check in')
    check_out = models.DateField('Tanggal check out')
    guests = models.PositiveSmallIntegerField('Jumlah tamu', default=1)
    notes = models.TextField('Catatan', blank=True)
    status = models.CharField(
        'Status',
        max_length=30,
        choices=Status.choices,
        default=Status.WAITING_PAYMENT,
    )
    source = models.CharField(
        'Sumber reservasi',
        max_length=20,
        choices=Source.choices,
        default=Source.ONLINE,
    )
    total = models.DecimalField('Total pembayaran', max_digits=14, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_reservations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    checked_in_at = models.DateTimeField(blank=True, null=True)
    checked_out_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Reservasi'
        verbose_name_plural = 'Reservasi'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'check_in'], name='res_status_checkin_idx'),
            models.Index(fields=['status', 'check_out'], name='res_status_checkout_idx'),
            models.Index(fields=['customer', 'created_at'], name='res_customer_created_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(check_out__gt=models.F('check_in')),
                name='reservation_dates_valid',
            ),
            models.CheckConstraint(condition=Q(guests__gte=1), name='reservation_guests_gte_1'),
            models.CheckConstraint(condition=Q(total__gte=0), name='reservation_total_gte_0'),
        ]

    @property
    def nights(self):
        if self.check_in and self.check_out:
            return max((self.check_out - self.check_in).days, 0)
        return 0

    @property
    def room_count(self):
        count = self.reserved_rooms.count() if self.pk else 0
        return count or (1 if self.room_id else 0)

    @property
    def total_capacity(self):
        if self.pk and self.reserved_rooms.exists():
            return sum(item.room.room_type.capacity for item in self.reserved_rooms.select_related('room__room_type'))
        return self.room.room_type.capacity if self.room_id else 0

    def clean(self):
        errors = {}
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            errors['check_out'] = 'Tanggal check out harus setelah tanggal check in.'

        if self.room_id and self.guests and self.guests > self.total_capacity:
            errors['guests'] = f'Maksimal {self.total_capacity} tamu untuk kamar yang dipilih.'

        if (
            self.room_id
            and self.check_in
            and self.check_out
            and self.check_out > self.check_in
            and not self.room.is_available(
                check_in=self.check_in,
                check_out=self.check_out,
                exclude_reservation=self.pk,
            )
        ):
            errors['room'] = 'Kamar utama tidak tersedia pada rentang tanggal tersebut.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f'RH-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}'
        if self.room_id and self.check_in and self.check_out and not self.pk:
            self.total = Decimal(self.nights) * self.room.price
        super().save(*args, **kwargs)

    def recalculate_total(self, save=True):
        if self.pk and self.reserved_rooms.exists():
            nightly_total = sum(
                (item.price_per_night for item in self.reserved_rooms.all()),
                Decimal('0'),
            )
        elif self.room_id:
            nightly_total = self.room.price
        else:
            nightly_total = Decimal('0')
        self.total = Decimal(self.nights) * nightly_total
        if save:
            self.save(update_fields=['total', 'updated_at'])
        return self.total

    def ensure_stay_record(self):
        record, _ = StayRecord.objects.get_or_create(reservation=self)
        return record

    def __str__(self):
        return self.code


class ReservationRoom(models.Model):
    class KeyStatus(models.TextChoices):
        NOT_GIVEN = 'NOT_GIVEN', 'Belum diberikan'
        GIVEN = 'GIVEN', 'Sudah diberikan'
        RETURNED = 'RETURNED', 'Sudah dikembalikan'
        PROBLEM = 'PROBLEM', 'Hilang atau bermasalah'

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='reserved_rooms',
        verbose_name='Reservasi',
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='reservation_items',
        verbose_name='Kamar',
    )
    price_per_night = models.DecimalField('Harga per malam', max_digits=12, decimal_places=2)
    key_status = models.CharField(
        'Status kunci',
        max_length=20,
        choices=KeyStatus.choices,
        default=KeyStatus.NOT_GIVEN,
    )
    key_given_at = models.DateTimeField('Waktu kunci diberikan', null=True, blank=True)
    key_given_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='keys_given',
        verbose_name='Kunci diberikan oleh',
    )
    key_returned_at = models.DateTimeField('Waktu kunci dikembalikan', null=True, blank=True)
    key_returned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='keys_received',
        verbose_name='Kunci diterima oleh',
    )
    key_notes = models.CharField('Catatan/kondisi kunci', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Kamar reservasi'
        verbose_name_plural = 'Kamar reservasi'
        ordering = ['room__number']
        constraints = [
            models.UniqueConstraint(
                fields=['reservation', 'room'],
                name='unique_room_in_reservation',
            ),
        ]
        indexes = [
            models.Index(fields=['key_status'], name='reservation_key_status_idx'),
        ]

    def __str__(self):
        return f'{self.reservation} - {self.room}'


class StayRecord(models.Model):
    class KtpStatus(models.TextChoices):
        NOT_RECEIVED = 'NOT_RECEIVED', 'Belum diserahkan'
        HELD = 'HELD', 'Dititipkan sebagai jaminan'
        RETURNED = 'RETURNED', 'Sudah dikembalikan'

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='stay_record',
        verbose_name='Reservasi',
    )
    ktp_status = models.CharField(
        'Status jaminan KTP',
        max_length=20,
        choices=KtpStatus.choices,
        default=KtpStatus.NOT_RECEIVED,
    )
    ktp_received_at = models.DateTimeField('Waktu KTP diterima', null=True, blank=True)
    ktp_received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ktp_guarantees_received',
        verbose_name='KTP diterima oleh',
    )
    ktp_returned_at = models.DateTimeField('Waktu KTP dikembalikan', null=True, blank=True)
    ktp_returned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ktp_guarantees_returned',
        verbose_name='KTP dikembalikan oleh',
    )
    notes = models.TextField('Catatan jaminan KTP', blank=True)

    class Meta:
        verbose_name = 'Catatan menginap dan jaminan'
        verbose_name_plural = 'Catatan menginap dan jaminan'
        indexes = [models.Index(fields=['ktp_status'], name='stay_ktp_status_idx')]

    @property
    def identity_verified(self):
        profile = getattr(self.reservation.customer, 'customer_profile', None)
        return bool(profile and profile.identity_is_verified)

    @property
    def all_keys_given(self):
        items = self.reservation.reserved_rooms.all()
        return bool(items) and all(item.key_status == ReservationRoom.KeyStatus.GIVEN for item in items)

    @property
    def all_keys_returned(self):
        items = self.reservation.reserved_rooms.all()
        return bool(items) and all(item.key_status == ReservationRoom.KeyStatus.RETURNED for item in items)

    def __str__(self):
        return f'Operasional {self.reservation.code}'


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Menunggu Verifikasi'
        VERIFIED = 'VERIFIED', 'Terverifikasi'
        REJECTED = 'REJECTED', 'Ditolak'

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name='Reservasi',
    )
    amount = models.DecimalField('Jumlah pembayaran', max_digits=14, decimal_places=2)
    proof = models.ImageField('Bukti transfer', upload_to='payment_proofs/', blank=True)
    status = models.CharField(
        'Status pembayaran',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    paid_at = models.DateTimeField('Tanggal pembayaran', default=timezone.now)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField('Catatan verifikasi', blank=True)

    class Meta:
        verbose_name = 'Pembayaran'
        verbose_name_plural = 'Pembayaran'
        ordering = ['-paid_at']
        indexes = [models.Index(fields=['status', 'verified_at'], name='pay_status_verified_idx')]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name='payment_amount_gt_0')]

    def __str__(self):
        return f'Pembayaran {self.reservation.code}'


class HotelSetting(models.Model):
    name = models.CharField('Nama hotel', max_length=150, default='RoseHaven Hotel')
    tagline = models.CharField(
        'Tagline',
        max_length=200,
        default='A timeless stay, wrapped in comfort.',
    )
    description = models.TextField(
        'Tentang hotel',
        default=(
            'RoseHaven adalah hotel bintang 4 dengan pelayanan '
            'hangat, kamar elegan, dan fasilitas lengkap.'
        ),
    )
    address = models.TextField('Alamat', default='Jl. Mawar Indah No. 8, Indonesia')
    phone = models.CharField('No. telepon', max_length=30, default='+62 812-3456-7890')
    email = models.EmailField('Email', default='hello@rosehaven.test')
    bank_name = models.CharField('Nama bank', max_length=80, default='Bank RoseHaven')
    bank_account = models.CharField('Nomor rekening', max_length=80, default='1234567890')
    bank_holder = models.CharField('Atas nama', max_length=100, default='RoseHaven Hotel')

    class Meta:
        verbose_name = 'Pengaturan hotel'
        verbose_name_plural = 'Pengaturan hotel'

    def __str__(self):
        return self.name
