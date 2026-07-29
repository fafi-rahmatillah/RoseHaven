from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rosehaven.decorators import role_required
from rosehaven.utils import apply_validation_error
from administrator.models import Payment, Reservation, Room
from .forms import PaymentVerificationForm, WalkInReservationForm

STAFF_ONLY = role_required('Resepsionis')


@STAFF_ONLY
def dashboard(request):
    today = timezone.localdate()
    context = {
        'new_reservations': Reservation.objects.filter(created_at__date=today).count(),
        'waiting_payments': Payment.objects.filter(status=Payment.Status.PENDING).count(),
        'today_checkins': Reservation.objects.filter(check_in=today).exclude(status=Reservation.Status.CANCELED).count(),
        'today_checkouts': Reservation.objects.filter(check_out=today).exclude(status=Reservation.Status.CANCELED).count(),
        'recent': Reservation.objects.select_related('customer', 'room')[:8],
    }
    return render(request, 'resepsionis/dashboard.html', context)


@STAFF_ONLY
def reservation_list(request):
    reservations = Reservation.objects.select_related('customer', 'room').all()
    status = request.GET.get('status', '')
    if status:
        reservations = reservations.filter(status=status)
    return render(request, 'resepsionis/reservation_list.html', {'reservations': reservations, 'statuses': Reservation.Status.choices, 'selected_status': status})


@STAFF_ONLY
def walk_in_add(request):
    form = WalkInReservationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        customer = form.get_or_create_customer()
        reservation = form.save(commit=False)
        reservation.customer = customer
        reservation.created_by = request.user
        reservation.source = Reservation.Source.WALK_IN
        reservation.status = Reservation.Status.WAITING_PAYMENT
        try:
            reservation.full_clean()
            reservation.save()
        except Exception as exc:
            apply_validation_error(form, exc)
        else:
            messages.success(request, f'Reservasi datang langsung {reservation.code} berhasil dibuat.')
            return redirect('resepsionis:reservation_list')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Tambah Reservasi Datang Langsung', 'back_url': 'resepsionis:reservation_list'})


@STAFF_ONLY
def customer_list(request):
    users = User.objects.filter(groups__name='Customer').select_related('customer_profile').distinct().order_by('first_name')
    return render(request, 'resepsionis/customer_list.html', {'users': users})


@STAFF_ONLY
def room_list(request):
    rooms = Room.objects.select_related('room_type').order_by('number')
    return render(request, 'resepsionis/room_list.html', {'rooms': rooms})


@STAFF_ONLY
def payment_list(request):
    payments = Payment.objects.select_related('reservation', 'reservation__customer', 'reservation__room').all()
    return render(request, 'resepsionis/payment_list.html', {'payments': payments})


@STAFF_ONLY
def verify_payment(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('reservation'), pk=pk)
    form = PaymentVerificationForm(request.POST or None, instance=payment)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.verified_by = request.user
        obj.verified_at = timezone.now()
        obj.save()
        reservation = obj.reservation
        if obj.status == Payment.Status.VERIFIED:
            reservation.status = Reservation.Status.CONFIRMED
            messages.success(request, 'Pembayaran terverifikasi dan reservasi dikonfirmasi.')
        elif obj.status == Payment.Status.REJECTED:
            reservation.status = Reservation.Status.WAITING_PAYMENT
            messages.warning(request, 'Pembayaran ditolak. Customer dapat mengunggah bukti baru.')
        reservation.save(update_fields=['status', 'updated_at'])
        return redirect('resepsionis:payment_list')
    return render(request, 'resepsionis/payment_verify.html', {'form': form, 'payment': payment})


@STAFF_ONLY
def check_in_list(request):
    reservations = Reservation.objects.select_related('customer', 'room').filter(status__in=[Reservation.Status.CONFIRMED, Reservation.Status.PAID]).order_by('check_in')
    return render(request, 'resepsionis/check_in.html', {'reservations': reservations})


@STAFF_ONLY
def check_in_action(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.method == 'POST':
        if reservation.status not in [Reservation.Status.CONFIRMED, Reservation.Status.PAID]:
            messages.error(request, 'Reservasi belum dapat diproses check in.')
        elif reservation.room.status == Room.Status.MAINTENANCE:
            messages.error(request, 'Kamar sedang dalam perawatan.')
        else:
            reservation.status = Reservation.Status.CHECKED_IN
            reservation.checked_in_at = timezone.now()
            reservation.save(update_fields=['status', 'checked_in_at', 'updated_at'])
            reservation.room.status = Room.Status.OCCUPIED
            reservation.room.save(update_fields=['status'])
            messages.success(request, f'Check in {reservation.code} berhasil.')
    return redirect('resepsionis:check_in_list')


@STAFF_ONLY
def check_out_list(request):
    reservations = Reservation.objects.select_related('customer', 'room').filter(status=Reservation.Status.CHECKED_IN).order_by('check_out')
    return render(request, 'resepsionis/check_out.html', {'reservations': reservations})


@STAFF_ONLY
def check_out_action(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, status=Reservation.Status.CHECKED_IN)
    if request.method == 'POST':
        reservation.status = Reservation.Status.CHECKED_OUT
        reservation.checked_out_at = timezone.now()
        reservation.save(update_fields=['status', 'checked_out_at', 'updated_at'])
        reservation.room.status = Room.Status.AVAILABLE
        reservation.room.save(update_fields=['status'])
        messages.success(request, f'Check out {reservation.code} berhasil.')
    return redirect('resepsionis:check_out_list')


@STAFF_ONLY
def schedule(request):
    reservations = Reservation.objects.select_related('customer', 'room').exclude(status=Reservation.Status.CANCELED).order_by('check_in', 'room__number')
    return render(request, 'resepsionis/schedule.html', {'reservations': reservations})
