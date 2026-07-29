from django.contrib.auth.models import User
from django.db import models


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField('No. HP', max_length=30)
    address = models.TextField('Alamat')

    class Meta:
        verbose_name = 'Profil customer'
        verbose_name_plural = 'Profil customer'

    def __str__(self):
        return self.user.get_full_name() or self.user.username
