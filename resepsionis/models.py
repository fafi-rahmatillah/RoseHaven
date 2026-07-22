from django.contrib.auth.models import User
from django.db import models


class ReceptionistProfile(models.Model):
    class Shift(models.TextChoices):
        MORNING = 'MORNING', 'Pagi'
        AFTERNOON = 'AFTERNOON', 'Siang'
        NIGHT = 'NIGHT', 'Malam'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='receptionist_profile')
    phone = models.CharField('No. HP', max_length=30, blank=True)
    shift = models.CharField('Shift', max_length=20, choices=Shift.choices, default=Shift.MORNING)
    is_active = models.BooleanField('Aktif', default=True)

    class Meta:
        verbose_name = 'Profil resepsionis'
        verbose_name_plural = 'Profil resepsionis'

    def __str__(self):
        return self.user.get_full_name() or self.user.username
