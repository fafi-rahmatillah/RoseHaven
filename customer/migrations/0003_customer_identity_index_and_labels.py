import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0002_customerprofile_identity_method_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerprofile',
            name='identity_method',
            field=models.CharField(
                blank=True,
                choices=[
                    ('online', 'Pemeriksaan data online oleh petugas'),
                    ('face_to_face', 'Pemeriksaan KTP tatap muka'),
                ],
                max_length=20,
                verbose_name='Metode pemeriksaan identitas',
            ),
        ),
        migrations.AlterField(
            model_name='customerprofile',
            name='is_married',
            field=models.BooleanField(default=False, verbose_name='Sudah menikah'),
        ),
        migrations.AlterField(
            model_name='customerprofile',
            name='marriage_certificate',
            field=models.FileField(
                blank=True,
                help_text='Wajib bagi customer yang memilih status sudah menikah.',
                upload_to='identity_documents/marriage/',
                verbose_name='Bukti surat nikah',
            ),
        ),
        migrations.AlterField(
            model_name='customerprofile',
            name='nik',
            field=models.CharField(
                blank=True,
                help_text='NIK terdiri dari 16 digit dan digunakan untuk validasi identitas.',
                max_length=16,
                null=True,
                unique=True,
                verbose_name='NIK',
            ),
        ),
        migrations.AlterField(
            model_name='customerprofile',
            name='verified_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='verified_customers',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Diverifikasi oleh',
            ),
        ),
        migrations.AddIndex(
            model_name='customerprofile',
            index=models.Index(fields=['identity_status'], name='cust_identity_status_idx'),
        ),
    ]
