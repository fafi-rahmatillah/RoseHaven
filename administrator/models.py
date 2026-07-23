import secrets
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Facility(models.Model):
    name = models.CharField(
        'Nama fasilitas',
        max_length=100,
        unique=True,
    )
    icon = models.CharField(
        'Ikon/emoji',
        max_length=20,
        blank=True,
        default='✦',
    )
    description = models.CharField(
        'Keterangan',
        max_length=255,
        blank=True,
    )

    class Meta:
        verbose_name = 'Fasilitas'
        verbose_name_plural = 'Fasilitas'
        ordering = ['name']

    def __str__(self):
        return self.name


class RoomType(models.Model):
    name = models.CharField(
        'Nama tipe',
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        'Deskripsi',
        blank=True,
    )
    base_price = models.DecimalField(
        'Harga dasar per malam',
        max_digits=12,
        decimal_places=2,
    )
    capacity = models.PositiveSmallIntegerField(
        'Kapasitas',
        default=2,
    )
    bed_type = models.CharField(
        'Jenis tempat tidur',
        max_length=100,
        default='Queen Bed',
    )
    size_m2 = models.PositiveSmallIntegerField(
        'Luas kamar (m²)',
        default=24,
    )

    class Meta:
        verbose_name = 'Tipe kamar'
        verbose_name_plural = 'Tipe kamar'
        ordering = ['base_price']
        constraints = [
            models.CheckConstraint(
                condition=Q(base_price__gte=0),
                name='roomtype_price_gte_0',
            ),
            models.CheckConstraint(
                condition=Q(capacity__gte=1),
                name='roomtype_capacity_gte_1',
            ),
            models.CheckConstraint(
                condition=Q(size_m2__gte=1),
                name='roomtype_size_gte_1',
            ),
        ]

    def __str__(self):
        return self.name


class Room(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Tersedia'
        OCCUPIED = 'OCCUPIED', 'Terisi'
        MAINTENANCE = 'MAINTENANCE', 'Perawatan'

    number = models.CharField(
        'Nomor kamar',
        max_length=20,
        unique=True,
    )
    name = models.CharField(
        'Nama kamar',
        max_length=120,
    )
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
    description = models.TextField(
        'Deskripsi',
        blank=True,
    )
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
    image = models.ImageField(
        'Foto kamar',
        upload_to='rooms/',
        blank=True,
    )
    is_active = models.BooleanField(
        'Aktif',
        default=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'Kamar'
        verbose_name_plural = 'Kamar'
        ordering = ['number']
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(custom_price__isnull=True)
                    | Q(custom_price__gte=0)
                ),
                name='room_custom_price_gte_0',
            ),
        ]

    @property
    def price(self):
        if self.custom_price is not None:
            return self.custom_price

        return self.room_type.base_price

    def is_available(
        self,
        check_in=None,
        check_out=None,
        exclude_reservation=None,
    ):
        if not self.is_active:
            return False

        if self.status == self.Status.MAINTENANCE:
            return False

        if not check_in or not check_out:
            return self.status == self.Status.AVAILABLE

        reservations = self.reservations.exclude(
            status__in=[
                Reservation.Status.CANCELED,
                Reservation.Status.COMPLETED,
            ]
        )

        if exclude_reservation:
            reservations = reservations.exclude(
                pk=exclude_reservation,
            )

        has_conflict = reservations.filter(
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).exists()

        return not has_conflict

    def __str__(self):
        return f'{self.number} - {self.name}'


class Reservation(models.Model):
    class Status(models.TextChoices):
        WAITING_PAYMENT = (
            'WAITING_PAYMENT',
            'Menunggu Pembayaran',
        )
        PAID = (
            'PAID',
            'Sudah Dibayar',
        )
        CONFIRMED = (
            'CONFIRMED',
            'Dikonfirmasi',
        )
        CHECKED_IN = (
            'CHECKED_IN',
            'Check In',
        )
        CHECKED_OUT = (
            'CHECKED_OUT',
            'Check Out',
        )
        COMPLETED = (
            'COMPLETED',
            'Selesai',
        )
        CANCELED = (
            'CANCELED',
            'Dibatalkan',
        )

    class Source(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        WALK_IN = 'WALK_IN', 'Datang Langsung'

    code = models.CharField(
        'Kode reservasi',
        max_length=24,
        unique=True,
        editable=False,
    )
    customer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='hotel_reservations',
        verbose_name='Customer',
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name='Kamar',
    )
    check_in = models.DateField(
        'Tanggal check in',
    )
    check_out = models.DateField(
        'Tanggal check out',
    )
    guests = models.PositiveSmallIntegerField(
        'Jumlah tamu',
        default=1,
    )
    notes = models.TextField(
        'Catatan',
        blank=True,
    )
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
    total = models.DecimalField(
        'Total pembayaran',
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_reservations',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    checked_in_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    checked_out_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Reservasi'
        verbose_name_plural = 'Reservasi'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    check_out__gt=models.F('check_in'),
                ),
                name='reservation_dates_valid',
            ),
            models.CheckConstraint(
                condition=Q(guests__gte=1),
                name='reservation_guests_gte_1',
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name='reservation_total_gte_0',
            ),
        ]

    @property
    def nights(self):
        if self.check_in and self.check_out:
            duration = (self.check_out - self.check_in).days
            return max(duration, 0)

        return 0

    def clean(self):
        errors = {}

        if (
            self.check_in
            and self.check_out
            and self.check_out <= self.check_in
        ):
            errors['check_out'] = (
                'Tanggal check out harus setelah tanggal check in.'
            )

        if (
            self.room_id
            and self.guests
            and self.guests > self.room.room_type.capacity
        ):
            errors['guests'] = (
                f'Maksimal {self.room.room_type.capacity} '
                'tamu untuk kamar ini.'
            )

        if (
            self.room_id
            and self.check_in
            and self.check_out
            and self.check_out > self.check_in
        ):
            room_available = self.room.is_available(
                check_in=self.check_in,
                check_out=self.check_out,
                exclude_reservation=self.pk,
            )

            if not room_available:
                errors['room'] = (
                    'Kamar tidak tersedia pada rentang tanggal tersebut.'
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.code:
            random_code = secrets.token_hex(3).upper()
            date_code = timezone.now().strftime('%Y%m%d')
            self.code = f'RH-{date_code}-{random_code}'

        if self.room_id and self.check_in and self.check_out:
            self.total = Decimal(self.nights) * self.room.price

        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = (
            'PENDING',
            'Menunggu Verifikasi',
        )
        VERIFIED = (
            'VERIFIED',
            'Terverifikasi',
        )
        REJECTED = (
            'REJECTED',
            'Ditolak',
        )

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name='Reservasi',
    )
    amount = models.DecimalField(
        'Jumlah pembayaran',
        max_digits=14,
        decimal_places=2,
    )
    proof = models.ImageField(
        'Bukti transfer',
        upload_to='payment_proofs/',
        blank=True,
    )
    status = models.CharField(
        'Status pembayaran',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    paid_at = models.DateTimeField(
        'Tanggal pembayaran',
        default=timezone.now,
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
    )
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    notes = models.TextField(
        'Catatan verifikasi',
        blank=True,
    )

    class Meta:
        verbose_name = 'Pembayaran'
        verbose_name_plural = 'Pembayaran'
        ordering = ['-paid_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='payment_amount_gt_0',
            ),
        ]

    def __str__(self):
        return f'Pembayaran {self.reservation.code}'


class HotelSetting(models.Model):
    name = models.CharField(
        'Nama hotel',
        max_length=150,
        default='RoseHaven Hotel',
    )
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
    address = models.TextField(
        'Alamat',
        default='Jl. Mawar Indah No. 8, Indonesia',
    )
    phone = models.CharField(
        'No. telepon',
        max_length=30,
        default='+62 812-3456-7890',
    )
    email = models.EmailField(
        'Email',
        default='hello@rosehaven.test',
    )
    bank_name = models.CharField(
        'Nama bank',
        max_length=80,
        default='Bank RoseHaven',
    )
    bank_account = models.CharField(
        'Nomor rekening',
        max_length=80,
        default='1234567890',
    )
    bank_holder = models.CharField(
        'Atas nama',
        max_length=100,
        default='RoseHaven Hotel',
    )

    class Meta:
        verbose_name = 'Pengaturan hotel'
        verbose_name_plural = 'Pengaturan hotel'

    def __str__(self):
        return self.name