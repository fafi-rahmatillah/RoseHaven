from administrator.models import HotelSetting


def global_context(request):
    setting = HotelSetting.objects.first()
    roles = set()
    if request.user.is_authenticated:
        roles = set(request.user.groups.values_list('name', flat=True))
    return {
        'hotel': setting,
        'is_administrator': request.user.is_authenticated and (
            request.user.is_superuser or 'Administrator' in roles
        ),
        'is_resepsionis': request.user.is_authenticated and 'Resepsionis' in roles,
        'is_customer': request.user.is_authenticated and 'Customer' in roles,
    }
