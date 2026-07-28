from django.db import migrations


def merge_validation_role(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')

    ReceptionistProfile = apps.get_model(
        'resepsionis',
        'ReceptionistProfile',
    )

    receptionist_group, _ = Group.objects.get_or_create(
        name='Resepsionis'
    )

    legacy_group = Group.objects.filter(
        name='Petugas Validasi'
    ).first()

    if not legacy_group:
        return

    for user in User.objects.filter(groups=legacy_group):
        user.groups.add(receptionist_group)

        ReceptionistProfile.objects.get_or_create(
            user=user,
            defaults={
                'phone': '',
                'shift': 'MORNING',
                'is_active': user.is_active,
            },
        )

    legacy_group.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('resepsionis', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            merge_validation_role,
            migrations.RunPython.noop,
        ),
    ]