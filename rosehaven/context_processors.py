from administrator.models import HotelSetting


def global_context(request):
    setting = HotelSetting.objects.first()
    return {
        'hotel': setting,
        'is_administrator': request.user.is_authenticated and (request.user.is_superuser or request.user.groups.filter(name='Administrator').exists()),
        'is_resepsionis': request.user.is_authenticated and request.user.groups.filter(name='Resepsionis').exists(),
        'is_customer': request.user.is_authenticated and request.user.groups.filter(name='Customer').exists(),
    }
