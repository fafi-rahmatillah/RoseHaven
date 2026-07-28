from datetime import datetime

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from rosehaven.decorators import role_required
from rosehaven.reservations_services import (
    sync_reservation_rooms,
)
from rosehaven.utils import apply_validation_error

from .forms import (
    FacilityForm,
    HotelSettingForm,
    PaymentAdminForm,
    ReservationAdminForm,
    RoomForm,
    RoomTypeForm,
    UserAccountForm,
)
from .models import (
    Facility,
    HotelSetting,
    Payment,
    Reservation,
    Room,
    RoomType,
)


ADMIN_ONLY = role_required('Administrator')


def _date_filters(
    request,
    queryset,
    field='created_at',
):
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')

    try:
        if start:
            start_date = datetime.strptime(
                start,
                '%Y-%m-%d',
            ).date()

            queryset = queryset.filter(
                **{
                    f'{field}__date__gte': (
                        start_date
                    )
                }
            )

        if end:
            end_date = datetime.strptime(
                end,
                '%Y-%m-%d',
            ).date()

            queryset = queryset.filter(
                **{
                    f'{field}__date__lte': (
                        end_date
                    )
                }
            )

    except ValueError:
        messages.error(
            request,
            'Format tanggal tidak valid.',
        )

    return queryset, start, end


@ADMIN_ONLY
def dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    verified_payments = Payment.objects.filter(
        status=Payment.Status.VERIFIED,
        verified_at__date__gte=month_start,
    )

    context = {
        'total_rooms': Room.objects.count(),

        'available_rooms': (
            Room.objects
            .filter(
                status=Room.Status.AVAILABLE,
                is_active=True,
            )
            .count()
        ),

        'occupied_rooms': (
            Room.objects
            .filter(
                status=Room.Status.OCCUPIED
            )
            .count()
        ),

        'total_customers': (
            User.objects
            .filter(groups__name='Customer')
            .distinct()
            .count()
        ),

        'total_reservations': (
            Reservation.objects.count()
        ),

        'income_month': (
            verified_payments.aggregate(
                total=Sum('amount')
            )['total']
            or 0
        ),

        'today_reservations': (
            Reservation.objects
            .filter(created_at__date=today)
            .count()
        ),

        'today_checkins': (
            Reservation.objects
            .filter(check_in=today)
            .count()
        ),

        'today_checkouts': (
            Reservation.objects
            .filter(check_out=today)
            .count()
        ),

        'recent': (
            Reservation.objects
            .select_related(
                'customer',
                'room',
            )
            .prefetch_related(
                'reserved_rooms__room'
            )[:8]
        ),

        'status_summary': (
            Reservation.objects
            .values('status')
            .annotate(total=Count('id'))
            .order_by('status')
        ),
    }

    return render(
        request,
        'administrator/dashboard.html',
        context,
    )


@ADMIN_ONLY
def room_list(request):
    rooms = (
        Room.objects
        .select_related('room_type')
        .prefetch_related('facilities')
    )

    query = request.GET.get(
        'q',
        '',
    ).strip()

    if query:
        rooms = rooms.filter(
            Q(number__icontains=query)
            | Q(name__icontains=query)
            | Q(
                room_type__name__icontains=query
            )
        )

    return render(
        request,
        'administrator/room_list.html',
        {
            'rooms': rooms,
            'query': query,
        },
    )


@ADMIN_ONLY
def room_form(request, pk=None):
    room = (
        get_object_or_404(Room, pk=pk)
        if pk
        else None
    )

    form = RoomForm(
        request.POST or None,
        request.FILES or None,
        instance=room,
    )

    if (
        request.method == 'POST'
        and form.is_valid()
    ):
        form.save()

        messages.success(
            request,
            'Data kamar berhasil disimpan.',
        )

        return redirect(
            'administrator:room_list'
        )

    return render(
        request,
        'shared/form.html',
        {
            'form': form,
            'title': (
                'Edit Kamar'
                if room
                else 'Tambah Kamar'
            ),
            'back_url': (
                'administrator:room_list'
            ),
        },
    )


@ADMIN_ONLY
def room_delete(request, pk):
    room = get_object_or_404(
        Room,
        pk=pk,
    )

    if request.method == 'POST':
        try:
            room.delete()

            messages.success(
                request,
                'Kamar berhasil dihapus.',
            )

        except ProtectedError:
            messages.error(
                request,
                'Kamar tidak dapat dihapus '
                'karena sudah digunakan pada '
                'reservasi. Nonaktifkan kamar '
                'sebagai gantinya.',
            )

        return redirect(
            'administrator:room_list'
        )

    return render(
        request,
        'shared/confirm_delete.html',
        {
            'object': room,
            'title': 'Hapus Kamar',
            'back_url': (
                'administrator:room_list'
            ),
        },
    )


@ADMIN_ONLY
def room_type_list(request):
    items = RoomType.objects.annotate(
        room_count=Count('rooms')
    )

    return render(
        request,
        'administrator/room_type_list.html',
        {
            'items': items,
        },
    )


@ADMIN_ONLY
def room_type_form(request, pk=None):
    room_type = (
        get_object_or_404(RoomType, pk=pk)
        if pk
        else None
    )

    form = RoomTypeForm(
        request.POST or None,
        instance=room_type,
    )

    if (
        request.method == 'POST'
        and form.is_valid()
    ):
        form.save()

        messages.success(
            request,
            'Tipe kamar berhasil disimpan.',
        )

        return redirect(
            'administrator:room_type_list'
        )

    return render(
        request,
        'shared/form.html',
        {
            'form': form,
            'title': (
                'Edit Tipe Kamar'
                if room_type
                else 'Tambah Tipe Kamar'
            ),
            'back_url': (
                'administrator:room_type_list'
            ),
        },
    )


@ADMIN_ONLY
def room_type_delete(request, pk):
    room_type = get_object_or_404(
        RoomType,
        pk=pk,
    )

    if request.method == 'POST':
        try:
            room_type.delete()

            messages.success(
                request,
                'Tipe kamar berhasil dihapus.',
            )

        except ProtectedError:
            messages.error(
                request,
                'Tipe kamar masih digunakan '
                'dan tidak dapat dihapus.',
            )

        return redirect(
            'administrator:room_type_list'
        )

    return render(
        request,
        'shared/confirm_delete.html',
        {
            'object': room_type,
            'title': 'Hapus Tipe Kamar',
            'back_url': (
                'administrator:room_type_list'
            ),
        },
    )


@ADMIN_ONLY
def facility_list(request):
    items = Facility.objects.annotate(
        room_count=Count('rooms')
    )

    return render(
        request,
        'administrator/facility_list.html',
        {
            'items': items,
        },
    )


@ADMIN_ONLY
def facility_form(request, pk=None):
    facility = (
        get_object_or_404(Facility, pk=pk)
        if pk
        else None
    )

    form = FacilityForm(
        request.POST or None,
        instance=facility,
    )

    if (
        request.method == 'POST'
        and form.is_valid()
    ):
        form.save()

        messages.success(
            request,
            'Fasilitas berhasil disimpan.',
        )

        return redirect(
            'administrator:facility_list'
        )

    return render(
        request,
        'shared/form.html',
        {
            'form': form,
            'title': (
                'Edit Fasilitas'
                if facility
                else 'Tambah Fasilitas'
            ),
            'back_url': (
                'administrator:facility_list'
            ),
        },
    )


@ADMIN_ONLY
def facility_delete(request, pk):
    facility = get_object_or_404(
        Facility,
        pk=pk,
    )

    if request.method == 'POST':
        facility.delete()

        messages.success(
            request,
            'Fasilitas berhasil dihapus.',
        )

        return redirect(
            'administrator:facility_list'
        )

    return render(
        request,
        'shared/confirm_delete.html',
        {
            'object': facility,
            'title': 'Hapus Fasilitas',
            'back_url': (
                'administrator:facility_list'
            ),
        },
    )


@ADMIN_ONLY
def customer_list(request):
    users = (
        User.objects
        .filter(groups__name='Customer')
        .select_related('customer_profile')
        .distinct()
        .order_by('-date_joined')
    )

    return render(
        request,
        'administrator/customer_list.html',
        {
            'users': users,
        },
    )


@ADMIN_ONLY
def customer_form(request, pk=None):
    customer = (
        get_object_or_404(
            User,
            pk=pk,
            groups__name='Customer',
        )
        if pk
        else None
    )

    form = UserAccountForm(
        request.POST or None,
        instance=customer,
        role='Customer',
    )

    if (
        request.method == 'POST'
        and form.is_valid()
    ):
        form.save()

        messages.success(
            request,
            'Akun customer berhasil disimpan.',
        )

        return redirect(
            'administrator:customer_list'
        )

    return render(
        request,
        'shared/form.html',
        {
            'form': form,
            'title': (
                'Edit Customer'
                if customer
                else 'Tambah Customer'
            ),
            'back_url': (
                'administrator:customer_list'
            ),
        },
    )


@ADMIN_ONLY
def customer_delete(request, pk):
    customer = get_object_or_404(
        User,
        pk=pk,
        groups__name='Customer',
    )

    if request.method == 'POST':
        try:
            customer.delete()

            messages.success(
                request,
                'Akun customer berhasil dihapus.',
            )

        except ProtectedError:
            messages.error(
                request,
                'Akun customer memiliki reservasi '
                'dan tidak dapat dihapus. '
                'Nonaktifkan akun sebagai gantinya.',
            )

        return redirect(
            'administrator:customer_list'
        )

    return render(
        request,
        'shared/confirm_delete.html',
        {
            'object': customer,
            'title': 'Hapus Customer',
            'back_url': (
                'administrator:customer_list'
            ),
        },
    )


@ADMIN_ONLY
def reservation_list(request):
    reservations = (
        Reservation.objects
        .select_related(
            'customer',
            'room',
        )
        .prefetch_related(
            'reserved_rooms__room'
        )
    )

    selected_status = request.GET.get(
        'status',
        '',
    )

    if selected_status:
        reservations = reservations.filter(
            status=selected_status
        )

    return render(
        request,
        'administrator/reservation_list.html',
        {
            'reservations': reservations,
            'statuses': (
                Reservation.Status.choices
            ),
            'selected_status': selected_status,
        },
    )


@ADMIN_ONLY
def reservation_form(request, pk=None):
    reservation = (
        get_object_or_404(
            Reservation,
            pk=pk,
        )
        if pk
        else None
    )

    form = ReservationAdminForm(
        request.POST or None,
        instance=reservation,
    )

    if (
        request.method == 'POST'
        and form.is_valid()
    ):
        reservation_object = form.save(
            commit=False
        )

        rooms = list(
            form.cleaned_data['rooms']
        )

        reservation_object.room = rooms[0]

        reservation_object.created_by = (
            reservation_object.created_by
            or request.user
        )

        try:
            sync_reservation_rooms(
                reservation_object,
                rooms,
            )

        except Exception as error:
            apply_validation_error(
                form,
                error,
            )

        else:
            messages.success(
                request,
                'Reservasi berhasil disimpan.',
            )

            return redirect(
                'administrator:reservation_list'
            )

    return render(
        request,
        'shared/form.html',
        {
            'form': form,
            'title': (
                'Edit Reservasi'
                if reservation
                else 'Tambah Reservasi'
            ),
            'back_url': (
                'administrator:reservation_list'
            ),
        },
    )


@ADMIN_ONLY
def reservation_delete(request, pk):
    reservation = get_object_or_404(
        Reservation,
        pk=pk,
    )

    if request.method == 'POST':
        reservation.delete()

        messages.success(
            request,
            'Reservasi berhasil dihapus.',
        )

        return redirect(
            'administrator:reservation_list'
        )

    return render(
        request,
        'shared/confirm_delete.html',
        {
            'object': reservation,
            'title': 'Hapus Reservasi',
            'back_url': (
                'administrator:reservation_list'
            ),
        },
    )


@ADMIN_ONLY
def payment_list(request):
    payments = (
        Payment.objects
        .select_related(
            'reservation',
            'reservation__customer',
            'verified_by',
        )
        .prefetch_related(
            'reservation__reserved_rooms__room'
        )
    )

    return render(
        request,
        'administrator/payment_list.html',
        {
            'payments': payments,
        },
    )


@ADMIN_ONLY
def payment_form(request, pk):
    payment = get_object_or_404(
        Payment,
        pk=pk,
    )

    form = PaymentAdminForm(
        request.POST or None,
        request.FILES or None,
        instance=payment,
    )

    if (
        request.method == 'POST'
        and form.is_valid()
    ):
        payment_object = form.save(
            commit=False
        )

        if (
            payment_object.status
            == Payment.Status.VERIFIED
        ):
            payment_object.verified_by = (
                request.user
            )

            payment_object.verified_at = (
                timezone.now()
            )

            reservation = (
                payment_object.reservation
            )

            reservation.status = (
                Reservation.Status.CONFIRMED
            )

            reservation.save(
                update_fields=[
                    'status',
                    'updated_at',
                ]
            )

        payment_object.save()

        messages.success(
            request,
            'Pembayaran berhasil diperbarui.',
        )

        return redirect(
            'administrator:payment_list'
        )

    return render(
        request,
        'shared/form.html',
        {
            'form': form,
            'title': 'Edit Pembayaran',
            'back_url': (
                'administrator:payment_list'
            ),
        },
    )


@ADMIN_ONLY
def payment_delete(request, pk):
    payment = get_object_or_404(
        Payment,
        pk=pk,
    )

    if request.method == 'POST':
        reservation = payment.reservation
        payment.delete()

        if (
            reservation.status
            == Reservation.Status.PAID
        ):
            reservation.status = (
                Reservation
                .Status
                .WAITING_PAYMENT
            )

            reservation.save(
                update_fields=[
                    'status',
                    'updated_at',
                ]
            )

        messages.success(
            request,
            'Data pembayaran berhasil dihapus.',
        )

        return redirect(
            'administrator:payment_list'
        )

    return render(
        request,
        'shared/confirm_delete.html',
        {
            'object': payment,
            'title': 'Hapus Pembayaran',
            'back_url': (
                'administrator:payment_list'
            ),
        },
    )


@ADMIN_ONLY
def receptionist_list(request):
    users = (
        User.objects
        .filter(groups__name='Resepsionis')
        .select_related(
            'receptionist_profile'
        )
        .distinct()
        .order_by('first_name')
    )

    return render(
        request,
        'administrator/receptionist_list.html',
        {
            'users': users,
        },
    )


@ADMIN_ONLY
def receptionist_form(request, pk=None):
    receptionist = (
        get_object_or_404(
            User,
            pk=pk,
            groups__name='Resepsionis',
        )
        if pk
        else None
    )

    form = UserAccountForm(
        request.POST or None,
        instance=receptionist,
        role='Resepsionis',
    )

    if (
        request.method == 'POST'
        and form.is_valid()
    ):
        form.save()

        messages.success(
            request,
            'Akun resepsionis berhasil disimpan.',
        )

        return redirect(
            'administrator:receptionist_list'
        )

    return render(
        request,
        'shared/form.html',
        {
            'form': form,
            'title': (
                'Edit Resepsionis'
                if receptionist
                else 'Tambah Resepsionis'
            ),
            'back_url': (
                'administrator:receptionist_list'
            ),
        },
    )


@ADMIN_ONLY
def receptionist_delete(request, pk):
    receptionist = get_object_or_404(
        User,
        pk=pk,
        groups__name='Resepsionis',
    )

    if request.method == 'POST':
        receptionist.delete()

        messages.success(
            request,
            'Akun resepsionis berhasil dihapus.',
        )

        return redirect(
            'administrator:receptionist_list'
        )

    return render(
        request,
        'shared/confirm_delete.html',
        {
            'object': receptionist,
            'title': 'Hapus Resepsionis',
            'back_url': (
                'administrator:receptionist_list'
            ),
        },
    )


@ADMIN_ONLY
def reports(request):
    reservations, start, end = _date_filters(
        request,
        (
            Reservation.objects
            .select_related(
                'customer',
                'room',
            )
            .prefetch_related(
                'reserved_rooms__room'
            )
        ),
    )

    payments, _, _ = _date_filters(
        request,
        (
            Payment.objects
            .select_related('reservation')
            .filter(
                status=Payment.Status.VERIFIED
            )
        ),
        'verified_at',
    )

    context = {
        'reservations': reservations,
        'payments': payments,
        'start': start,
        'end': end,

        'total_income': (
            payments.aggregate(
                total=Sum('amount')
            )['total']
            or 0
        ),

        'total_reservations': (
            reservations.count()
        ),

        'occupied_count': (
            reservations.filter(
                status__in=[
                    Reservation.Status.CHECKED_IN,
                    Reservation.Status.CHECKED_OUT,
                    Reservation.Status.COMPLETED,
                ]
            )
            .count()
        ),
    }

    return render(
        request,
        'administrator/reports.html',
        context,
    )


@ADMIN_ONLY
def settings_view(request):
    setting, _ = (
        HotelSetting.objects.get_or_create(
            pk=1
        )
    )

    form = HotelSettingForm(
        request.POST or None,
        instance=setting,
    )

    if (
        request.method == 'POST'
        and form.is_valid()
    ):
        form.save()

        messages.success(
            request,
            'Pengaturan hotel berhasil disimpan.',
        )

        return redirect(
            'administrator:settings'
        )

    return render(
        request,
        'administrator/settings.html',
        {
            'form': form,
        },
    )