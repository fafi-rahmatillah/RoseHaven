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
        'pending': 'warning', 'verified': 'success', 'rejected': 'danger',
        'NOT_RECEIVED': 'warning', 'HELD': 'info', 'RETURNED': 'success',
        'NOT_GIVEN': 'warning', 'GIVEN': 'info', 'PROBLEM': 'danger',
    }
    return mapping.get(str(value), 'secondary')


@register.filter
def join_rooms(reservation):
    items = reservation.reserved_rooms.all()
    if items:
        return ', '.join(f'{item.room.number} - {item.room.name}' for item in items)
    if reservation.room_id:
        return f'{reservation.room.number} - {reservation.room.name}'
    return '-'
