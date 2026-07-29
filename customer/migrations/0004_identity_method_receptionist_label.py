from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0003_customer_identity_index_and_labels'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerprofile',
            name='identity_method',
            field=models.CharField(
                blank=True,
                choices=[
                    ('online', 'Pemeriksaan data online oleh resepsionis'),
                    ('face_to_face', 'Pemeriksaan KTP tatap muka'),
                ],
                max_length=20,
                verbose_name='Metode pemeriksaan identitas',
            ),
        ),
    ]
