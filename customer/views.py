from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from administrator.models import Payment, Reservation, Room
from rosehaven.decorators import role_required
from rosehaven.reservation_services import attach_booked_periods, sync_reservation_rooms
from .forms import (
    CustomerProfileForm,
    LoginForm,
    PaymentUploadForm,
    RegistrationForm,
    ReservationForm,
)
from .models import CustomerProfile


def home(request):
    rooms = (
        Room.objects.filter(is_active=True)
        .exclude(status=Room.Status.MAINTENANCE)
        .select_related('room_type')[:6]
    )
    return render(request, 'public/home.html', {'rooms': rooms})


def about(request):
    return render(request, 'public/about.html')


def public_rooms(request):
    rooms = Room.objects.filter(is_active=True).select_related('room_type').prefetch_related('facilities')
    q = request.GET.get('q', '').strip()
    if q:
        rooms = rooms.filter(
            Q(name__icontains=q)
            | Q(number__icontains=q)
            | Q(room_type__name__icontains=q)
        )
    return render(request, 'public/rooms.html', {'rooms': rooms, 'q': q})


def public_room_detail(request, pk):
    room = get_object_or_404(
        Room.objects.select_related('room_type').prefetch_related('facilities'),
        pk=pk,
        is_active=True,
    )
    return render(request, 'public/room_detail.html', {'room': room})


def contact(request):
    if request.method == 'POST':
        messages.success(request, 'Pesan Anda telah diterima. Tim RoseHaven akan segera menghubungi Anda.')
        return redirect('contact')
    return render(request, 'public/contact.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('role_redirect')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        identifier = form.cleaned_data['username'].strip()
        username = identifier
        if '@' in identifier:
            found = User.objects.filter(email__iexact=identifier).first()
            if found:
                username = found.username
        user = authenticate(request, username=username, password=form.cleaned_data['password'])
        if user:
            if not user.is_active:
                messages.error(request, 'Akun Anda sedang dinonaktifkan.')
            else:
                login(request, user)
                messages.success(request, f'Selamat datang, {user.get_full_name() or user.username}.')
                return redirect('role_redirect')
        else:
            messages.error(request, 'Username/email atau password salah.')
    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('role_redirect')
    form = RegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            names = form.cleaned_data['name'].strip().split(maxsplit=1)
            email = form.cleaned_data['email']
            base = email.split('@')[0].replace('.', '_')[:120] or 'customer'
            username = base
            i = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'
                i += 1
            user = User.objects.create_user(
                username=username,
                email=email,
                password=form.cleaned_data['password'],
                first_name=names[0],
                last_name=names[1] if len(names) > 1 else '',
            )
            group, _ = Group.objects.get_or_create(name='Customer')
            user.groups.add(group)
            CustomerProfile.objects.create(
                user=user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                nik=form.cleaned_data['nik'],
                is_married=form.cleaned_data['is_married'],
                marriage_certificate=form.cleaned_data.get('marriage_certificate'),
                identity_status=CustomerProfile.IdentityStatus.PENDING,
            )
        messages.success(
            request,
            f'Registrasi berhasil. Username Anda: {username}. Anda sudah dapat membuat reservasi; '
            'validasi KTP dilakukan sebelum check-in.',
        )
        return redirect('login')
    return render(request, 'auth/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Anda telah logout.')
    return redirect('home')


def role_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_superuser or request.user.groups.filter(name='Administrator').exists():
        return redirect('administrator:dashboard')
    if request.user.groups.filter(name='Resepsionis').exists():
        return redirect('resepsionis:dashboard')
    return redirect('customer:dashboard')


@role_required('Customer')
def dashboard(request):
    profile_obj, _ = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={'phone': '', 'address': ''},
    )
    reservations = (
        Reservation.objects.filter(customer=request.user)
        .select_related('room', 'stay_record')
        .prefetch_related('reserved_rooms__room')
        .order_by('-created_at')
    )
    active = reservations.exclude(
        status__in=[
            Reservation.Status.CANCELED,
            Reservation.Status.COMPLETED,
            Reservation.Status.CHECKED_OUT,
        ]
    ).first()
    stay_record = active.ensure_stay_record() if active else None
    return render(
        request,
        'customer/dashboard.html',
        {
            'active': active,
            'stay_record': stay_record,
            'profile_obj': profile_obj,
            'reservations': reservations[:5],
        },
    )


@role_required('Customer')
def profile(request):
    profile_obj, _ = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={'phone': '', 'address': ''},
    )
    form = CustomerProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=profile_obj,
        user=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('customer:profile')
    return render(request, 'customer/profile.html', {'form': form, 'profile_obj': profile_obj})


@role_required('Customer')
def rooms(request):
    room_list = attach_booked_periods(
        Room.objects.filter(is_active=True)
        .exclude(status=Room.Status.MAINTENANCE)
        .select_related('room_type')
        .prefetch_related('facilities')
    )
    return render(request, 'customer/rooms.html', {'rooms': room_list})


@role_required('Customer')
def room_detail(request, pk):
    room = get_object_or_404(
        Room.objects.select_related('room_type').prefetch_related('facilities'),
        pk=pk,
        is_active=True,
    )
    attach_booked_periods([room])
    return render(request, 'customer/room_detail.html', {'room': room})


@role_required('Customer')
def reserve(request, room_id=None):
    # Status validasi identitas sengaja TIDAK diperiksa di halaman ini.
    # Customer berstatus menunggu/ditolak tetap boleh membuat reservasi.
    # Validasi identitas dan jaminan KTP baru menjadi syarat saat check-in.
    room = get_object_or_404(Room, pk=room_id, is_active=True) if room_id else None
    form = ReservationForm(request.POST or None, room=room)
    available_rooms = attach_booked_periods(
        Room.objects.filter(is_active=True)
        .exclude(status=Room.Status.MAINTENANCE)
        .select_related('room_type')
    )
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            reservation = form.save(commit=False)
            selected_rooms = list(form.cleaned_data['rooms'])
            reservation.room = selected_rooms[0]
            reservation.customer = request.user
            reservation.created_by = request.user
            reservation.source = Reservation.Source.ONLINE
            reservation.status = Reservation.Status.WAITING_PAYMENT
            sync_reservation_rooms(reservation, selected_rooms)
        messages.success(
            request,
            f'Reservasi {reservation.code} berhasil dibuat. Silakan unggah bukti pembayaran. '
            'KTP asli akan diperiksa resepsionis dan dititipkan sebagai jaminan sebelum check-in.',
        )
        return redirect('customer:payment_upload', pk=reservation.pk)
    return render(
        request,
        'customer/reservation_form.html',
        {'form': form, 'selected_room': room, 'available_rooms': available_rooms},
    )


@role_required('Customer')
def payment_upload(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, customer=request.user)
    if reservation.status in [
        Reservation.Status.CANCELED,
        Reservation.Status.COMPLETED,
        Reservation.Status.CHECKED_OUT,
    ]:
        messages.error(request, 'Reservasi ini tidak dapat dibayar.')
        return redirect('customer:reservation_detail', pk=pk)
    payment = Payment.objects.filter(reservation=reservation).first()
    form = PaymentUploadForm(request.POST or None, request.FILES or None, instance=payment)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.reservation = reservation
        obj.amount = reservation.total
        obj.status = Payment.Status.PENDING
        obj.paid_at = timezone.now()
        obj.save()
        reservation.status = Reservation.Status.PAID
        reservation.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Bukti pembayaran berhasil diunggah dan menunggu verifikasi resepsionis.')
        return redirect('customer:reservation_detail', pk=pk)
    return render(
        request,
        'customer/payment.html',
        {'form': form, 'reservation': reservation, 'payment': payment},
    )


@role_required('Customer')
def history(request):
    reservations = (
        Reservation.objects.filter(customer=request.user)
        .select_related('room', 'room__room_type')
        .prefetch_related('reserved_rooms__room')
    )
    return render(request, 'customer/history.html', {'reservations': reservations})


@role_required('Customer')
def reservation_detail(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'room',
            'room__room_type',
            'customer__customer_profile',
            'stay_record',
        ).prefetch_related('reserved_rooms__room__room_type'),
        pk=pk,
        customer=request.user,
    )
    stay_record = reservation.ensure_stay_record()
    return render(
        request,
        'customer/reservation_detail.html',
        {'reservation': reservation, 'stay_record': stay_record},
    )


@role_required('Customer')
def cancel_reservation(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, customer=request.user)
    if request.method == 'POST':
        if reservation.status == Reservation.Status.WAITING_PAYMENT:
            reservation.status = Reservation.Status.CANCELED
            reservation.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Reservasi berhasil dibatalkan.')
        else:
            messages.error(request, 'Reservasi hanya dapat dibatalkan sebelum pembayaran dikonfirmasi.')
    return redirect('customer:reservation_detail', pk=pk)
