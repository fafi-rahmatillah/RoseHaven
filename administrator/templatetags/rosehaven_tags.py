from django import template
register = template.Library()

@register.filter
def rupiah(value):
    try:
        return f'Rp {float(value):,.0f}'.replace(',', '.')
    except (TypeError, ValueError):
        return 'Rp 0'

@register.filter
def status_class(value):
    mapping = {
        'AVAILABLE': 'success', 'OCCUPIED': 'danger', 'MAINTENANCE': 'warning',
        'WAITING_PAYMENT': 'warning', 'PAID': 'info', 'CONFIRMED': 'success',
        'CHECKED_IN': 'primary', 'CHECKED_OUT': 'secondary', 'COMPLETED': 'success', 'CANCELED': 'danger',
        'PENDING': 'warning', 'VERIFIED': 'success', 'REJECTED': 'danger',
    }
    return mapping.get(str(value), 'secondary')
