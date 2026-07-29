from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from administrator.models import Payment, Reservation, ReservationRoom, Room, StayRecord
from customer.models import CustomerProfile
from rosehaven.decorators import role_required
from rosehaven.reservation_services import sync_reservation_rooms
from .forms import (
    IdentityValidationForm, KeyReturnForm, KtpGuaranteeForm,
    PaymentVerificationForm, WalkInReservationForm,
)

STAFF_ONLY = role_required('Resepsionis')


@STAFF_ONLY
def dashboard(request):
    today = timezone.localdate()
    context = {
        'new_reservations': Reservation.objects.filter(created_at__date=today).count(),
        'waiting_payments': Payment.objects.filter(status=Payment.Status.PENDING).count(),
        'today_checkins': Reservation.objects.filter(check_in=today).exclude(status=Reservation.Status.CANCELED).count(),
        'today_checkouts': Reservation.objects.filter(check_out=today).exclude(status=Reservation.Status.CANCELED).count(),
        'recent': Reservation.objects.select_related('customer', 'room').prefetch_related('reserved_rooms__room')[:8],
        'pending_identity': CustomerProfile.objects.filter(identity_status=CustomerProfile.IdentityStatus.PENDING).count(),
        'held_ktp': StayRecord.objects.filter(ktp_status=StayRecord.KtpStatus.HELD).count(),
    }
    return render(request, 'resepsionis/dashboard.html', context)


@STAFF_ONLY
def reservation_list(request):
    reservations = Reservation.objects.select_related('customer', 'room').prefetch_related('reserved_rooms__room').all()
    status = request.GET.get('status', '')
    if status:
        reservations = reservations.filter(status=status)
    return render(request, 'resepsionis/reservation_list.html', {
        'reservations': reservations,
        'statuses': Reservation.Status.choices,
        'selected_status': status,
    })


@STAFF_ONLY
def reservation_detail(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'customer__customer_profile', 'room', 'stay_record'
        ).prefetch_related('reserved_rooms__room'),
        pk=pk,
    )
    stay_record = reservation.ensure_stay_record()
    return render(request, 'resepsionis/reservation_detail.html', {
        'reservation': reservation,
        'stay_record': stay_record,
    })


@STAFF_ONLY
def walk_in_add(request):
    form = WalkInReservationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            customer = form.get_or_create_customer()
            reservation = form.save(commit=False)
            rooms = list(form.cleaned_data['rooms'])
            reservation.room = rooms[0]
            reservation.customer = customer
            reservation.created_by = request.user
            reservation.source = Reservation.Source.WALK_IN
            reservation.status = Reservation.Status.WAITING_PAYMENT
            sync_reservation_rooms(reservation, rooms)
        messages.success(request, f'Reservasi datang langsung {reservation.code} berhasil dibuat.')
        return redirect('resepsionis:reservation_list')
    return render(request, 'shared/form.html', {
        'form': form,
        'title': 'Tambah Reservasi Datang Langsung',
        'back_url': 'resepsionis:reservation_list',
    })


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
    payments = (
        Payment.objects.select_related('reservation', 'reservation__customer', 'reservation__room')
        .prefetch_related('reservation__reserved_rooms__room')
    )
    return render(request, 'resepsionis/payment_list.html', {'payments': payments})


@STAFF_ONLY
def verify_payment(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related('reservation', 'reservation__customer')
        .prefetch_related('reservation__reserved_rooms__room'),
        pk=pk,
    )
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
    reservations = (
        Reservation.objects.select_related('customer__customer_profile', 'room', 'stay_record')
        .prefetch_related('reserved_rooms__room')
        .filter(status=Reservation.Status.CONFIRMED)
        .order_by('check_in')
    )
    return render(request, 'resepsionis/check_in.html', {'reservations': reservations})


@STAFF_ONLY
def check_in_action(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('customer__customer_profile', 'stay_record').prefetch_related('reserved_rooms__room'),
        pk=pk,
    )
    if request.method == 'POST':
        stay_record = reservation.ensure_stay_record()
        profile = getattr(reservation.customer, 'customer_profile', None)
        payment = getattr(reservation, 'payment', None)
        if reservation.status != Reservation.Status.CONFIRMED:
            messages.error(request, 'Reservasi belum dikonfirmasi.')
        elif not profile or not profile.identity_is_verified:
            messages.error(request, 'Identitas customer belum disetujui oleh resepsionis.')
        elif stay_record.ktp_status != StayRecord.KtpStatus.HELD:
            messages.error(request, 'KTP asli belum diterima sebagai jaminan.')
        elif not payment or payment.status != Payment.Status.VERIFIED:
            messages.error(request, 'Pembayaran belum terverifikasi.')
        elif not reservation.reserved_rooms.exists():
            messages.error(request, 'Data kamar reservasi belum lengkap. Hubungi administrator.')
        else:
            now = timezone.now()
            reservation.status = Reservation.Status.CHECKED_IN
            reservation.checked_in_at = now
            reservation.save(update_fields=['status', 'checked_in_at', 'updated_at'])
            for item in reservation.reserved_rooms.select_related('room'):
                item.key_status = ReservationRoom.KeyStatus.GIVEN
                item.key_given_at = now
                item.key_given_by = request.user
                item.save(update_fields=['key_status', 'key_given_at', 'key_given_by'])
                item.room.status = Room.Status.OCCUPIED
                item.room.save(update_fields=['status'])
            messages.success(request, f'Check-in {reservation.code} berhasil dan seluruh kunci tercatat sudah diberikan.')
    return redirect('resepsionis:reservation_detail', pk=pk)


@STAFF_ONLY
def check_out_list(request):
    reservations = (
        Reservation.objects.select_related('customer', 'room', 'stay_record')
        .prefetch_related('reserved_rooms__room')
        .filter(status=Reservation.Status.CHECKED_IN)
        .order_by('check_out')
    )
    return render(request, 'resepsionis/check_out.html', {'reservations': reservations})


@STAFF_ONLY
def key_return_action(request, item_pk):
    item = get_object_or_404(
        ReservationRoom.objects.select_related('reservation', 'room'),
        pk=item_pk,
        reservation__status=Reservation.Status.CHECKED_IN,
    )
    if request.method == 'POST':
        form = KeyReturnForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data['status']
            item.key_status = status
            item.key_notes = form.cleaned_data['notes']
            item.key_returned_by = request.user
            item.key_returned_at = timezone.now() if status == ReservationRoom.KeyStatus.RETURNED else None
            item.save(update_fields=['key_status', 'key_notes', 'key_returned_by', 'key_returned_at'])
            if status == ReservationRoom.KeyStatus.RETURNED:
                messages.success(request, f'Kunci kamar {item.room.number} tercatat sudah dikembalikan.')
            else:
                messages.warning(request, f'Kunci kamar {item.room.number} ditandai bermasalah.')
    return redirect('resepsionis:reservation_detail', pk=item.reservation_id)


@STAFF_ONLY
def check_out_action(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.prefetch_related('reserved_rooms__room'),
        pk=pk,
        status=Reservation.Status.CHECKED_IN,
    )
    if request.method == 'POST':
        items = list(reservation.reserved_rooms.select_related('room'))
        if not items or any(item.key_status != ReservationRoom.KeyStatus.RETURNED for item in items):
            messages.error(request, 'Check-out belum dapat diselesaikan. Semua kunci harus dikembalikan terlebih dahulu.')
        else:
            reservation.status = Reservation.Status.CHECKED_OUT
            reservation.checked_out_at = timezone.now()
            reservation.save(update_fields=['status', 'checked_out_at', 'updated_at'])
            for item in items:
                item.room.status = Room.Status.AVAILABLE
                item.room.save(update_fields=['status'])
            messages.success(request, f'Check-out {reservation.code} berhasil. KTP sekarang dapat dikembalikan oleh resepsionis.')
    return redirect('resepsionis:reservation_detail', pk=pk)


@STAFF_ONLY
def schedule(request):
    items = (
        ReservationRoom.objects.select_related('reservation__customer', 'room')
        .exclude(reservation__status=Reservation.Status.CANCELED)
        .order_by('reservation__check_in', 'room__number')
    )
    return render(request, 'resepsionis/schedule.html', {'items': items})


@STAFF_ONLY
def identity_list(request):
    status = request.GET.get('status', '')
    profiles = CustomerProfile.objects.select_related('user', 'verified_by').order_by(
        'identity_status', 'user__first_name'
    )
    if status:
        profiles = profiles.filter(identity_status=status)
    return render(request, 'resepsionis/identity_list.html', {
        'profiles': profiles,
        'statuses': CustomerProfile.IdentityStatus.choices,
        'selected_status': status,
    })


@STAFF_ONLY
def identity_detail(request, pk):
    profile = get_object_or_404(
        CustomerProfile.objects.select_related('user', 'verified_by'), pk=pk
    )
    reservations = profile.user.hotel_reservations.select_related('stay_record').prefetch_related(
        'reserved_rooms__room'
    )
    return render(request, 'resepsionis/identity_detail.html', {
        'profile': profile,
        'reservations': reservations,
    })


@STAFF_ONLY
def validate_identity(request, pk):
    profile = get_object_or_404(CustomerProfile.objects.select_related('user'), pk=pk)
    form = IdentityValidationForm(request.POST or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        if obj.identity_status == CustomerProfile.IdentityStatus.PENDING:
            obj.identity_method = ''
            obj.identity_notes = ''
            obj.verified_by = None
            obj.verified_at = None
        else:
            obj.verified_by = request.user
            obj.verified_at = timezone.now()
        obj.save()
        if obj.identity_status == CustomerProfile.IdentityStatus.VERIFIED:
            messages.success(request, 'Identitas customer berhasil disetujui oleh resepsionis.')
        elif obj.identity_status == CustomerProfile.IdentityStatus.REJECTED:
            messages.warning(request, 'Identitas customer ditolak dan alasan telah dicatat.')
        else:
            messages.info(request, 'Status identitas dikembalikan menjadi menunggu validasi.')
        return redirect('resepsionis:identity_detail', pk=profile.pk)
    return render(request, 'resepsionis/identity_form.html', {'form': form, 'profile': profile})


@STAFF_ONLY
def ktp_guarantee_list(request):
    reservations = (
        Reservation.objects.select_related('customer__customer_profile', 'stay_record')
        .prefetch_related('reserved_rooms__room')
        .exclude(status=Reservation.Status.CANCELED)
        .order_by('check_in')
    )
    for reservation in reservations:
        if not hasattr(reservation, 'stay_record'):
            reservation.ensure_stay_record()
    return render(request, 'resepsionis/ktp_list.html', {'reservations': reservations})


@STAFF_ONLY
def receive_ktp(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('customer__customer_profile', 'stay_record'),
        pk=pk,
    )
    stay_record = reservation.ensure_stay_record()
    form = KtpGuaranteeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        profile = reservation.customer.customer_profile
        if not profile.identity_is_verified:
            messages.error(request, 'KTP belum dapat diterima sebagai jaminan karena identitas belum disetujui.')
        elif reservation.status in [Reservation.Status.CANCELED, Reservation.Status.COMPLETED, Reservation.Status.CHECKED_OUT]:
            messages.error(request, 'Status reservasi tidak memungkinkan penerimaan jaminan KTP.')
        else:
            stay_record.ktp_status = StayRecord.KtpStatus.HELD
            stay_record.ktp_received_at = timezone.now()
            stay_record.ktp_received_by = request.user
            stay_record.notes = form.cleaned_data['notes']
            stay_record.save()
            messages.success(request, 'KTP asli tercatat telah diterima resepsionis sebagai jaminan.')
        return redirect('resepsionis:ktp_guarantee_list')
    return render(request, 'resepsionis/ktp_form.html', {
        'form': form,
        'reservation': reservation,
        'action_title': 'Terima KTP sebagai Jaminan',
    })


@STAFF_ONLY
def return_ktp(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('customer__customer_profile', 'stay_record').prefetch_related('reserved_rooms'),
        pk=pk,
    )
    stay_record = reservation.ensure_stay_record()
    form = KtpGuaranteeForm(request.POST or None, initial={'notes': stay_record.notes})
    if request.method == 'POST' and form.is_valid():
        all_keys_returned = reservation.reserved_rooms.exists() and not reservation.reserved_rooms.exclude(
            key_status=ReservationRoom.KeyStatus.RETURNED
        ).exists()
        if reservation.status != Reservation.Status.CHECKED_OUT:
            messages.error(request, 'KTP hanya dapat dikembalikan setelah proses check-out selesai.')
        elif not all_keys_returned:
            messages.error(request, 'KTP belum dapat dikembalikan karena masih ada kunci yang belum dikembalikan.')
        elif stay_record.ktp_status != StayRecord.KtpStatus.HELD:
            messages.error(request, 'KTP tidak sedang tercatat sebagai jaminan.')
        else:
            stay_record.ktp_status = StayRecord.KtpStatus.RETURNED
            stay_record.ktp_returned_at = timezone.now()
            stay_record.ktp_returned_by = request.user
            stay_record.notes = form.cleaned_data['notes']
            stay_record.save()
            reservation.status = Reservation.Status.COMPLETED
            reservation.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'KTP asli telah dikembalikan dan reservasi dinyatakan selesai.')
        return redirect('resepsionis:ktp_guarantee_list')
    return render(request, 'resepsionis/ktp_form.html', {
        'form': form,
        'reservation': reservation,
        'action_title': 'Kembalikan KTP Customer',
    })
