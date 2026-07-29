from django.contrib.auth.models import User
from django.db import models


class CustomerProfile(models.Model):
    class IdentityStatus(models.TextChoices):
        PENDING = 'pending', 'Menunggu validasi'
        VERIFIED = 'verified', 'Terverifikasi'
        REJECTED = 'rejected', 'Ditolak'

    class IdentityMethod(models.TextChoices):
        ONLINE = 'online', 'Pemeriksaan data online oleh resepsionis'
        FACE_TO_FACE = 'face_to_face', 'Pemeriksaan KTP tatap muka'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile',
    )
    phone = models.CharField('No. HP', max_length=30)
    address = models.TextField('Alamat')
    nik = models.CharField(
        'NIK',
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        help_text='NIK terdiri dari 16 digit dan digunakan untuk validasi identitas.',
    )
    is_married = models.BooleanField(
        'Sudah menikah',
        default=False,
    )
    marriage_certificate = models.FileField(
        'Bukti surat nikah',
        upload_to='identity_documents/marriage/',
        blank=True,
        help_text='Wajib bagi customer yang memilih status sudah menikah.',
    )
    identity_status = models.CharField(
        'Status validasi identitas',
        max_length=20,
        choices=IdentityStatus.choices,
        default=IdentityStatus.PENDING,
    )
    identity_method = models.CharField(
        'Metode pemeriksaan identitas',
        max_length=20,
        choices=IdentityMethod.choices,
        blank=True,
    )
    identity_notes = models.TextField(
        'Catatan pemeriksaan',
        blank=True,
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_customers',
        verbose_name='Diverifikasi oleh',
    )
    verified_at = models.DateTimeField(
        'Waktu verifikasi',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Profil customer'
        verbose_name_plural = 'Profil customer'
        indexes = [
            models.Index(fields=['identity_status'], name='cust_identity_status_idx'),
        ]

    @property
    def masked_nik(self):
        if not self.nik:
            return '-'
        if len(self.nik) <= 4:
            return self.nik
        return f'{self.nik[:2]}{"*" * (len(self.nik) - 4)}{self.nik[-2:]}'

    @property
    def identity_is_verified(self):
        return self.identity_status == self.IdentityStatus.VERIFIED

    def __str__(self):
        return self.user.get_full_name() or self.user.username
