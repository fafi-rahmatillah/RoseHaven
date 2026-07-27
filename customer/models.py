from django.contrib.auth.models import User
from django.db import models


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField('No. HP', max_length=30)
    address = models.TextField('Alamat')
    nik = models.CharField(
    'NIK',
    max_length=16,
    unique=True,
    null=True,
    blank=True,
)

    is_married = models.BooleanField(
        'Pasangan suami istri',
        default=False,
    )

    marriage_certificate = models.FileField(
        'Bukti surat nikah',
        upload_to='identity_documents/marriage/',
        blank=True,
    )

    identity_status = models.CharField(
        'Status validasi identitas',
        max_length=20,
        choices=[
            ('pending', 'Menunggu validasi'),
            ('verified', 'Terverifikasi'),
            ('rejected', 'Ditolak'),
        ],
        default='pending',
    )

    identity_method = models.CharField(
        'Metode pemeriksaan identitas',
        max_length=20,
        choices=[
            ('online', 'Pemeriksaan online'),
            ('face_to_face', 'Pemeriksaan tatap muka'),
        ],
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
    )

    verified_at = models.DateTimeField(
        'Waktu verifikasi',
        null=True,
        blank=True,
    )
    
    

    class Meta:
        verbose_name = 'Profil customer'
        verbose_name_plural = 'Profil customer'

    def __str__(self):
        return self.user.get_full_name() or self.user.username
