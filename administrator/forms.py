from django import forms
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from customer.models import CustomerProfile
from resepsionis.models import ReceptionistProfile
from .models import Facility, HotelSetting, Payment, Reservation, Room, RoomType


class StyledModelForm(forms.ModelForm):
    pass


class RoomTypeForm(StyledModelForm):
    class Meta:
        model = RoomType
        fields = '__all__'
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class FacilityForm(StyledModelForm):
    class Meta:
        model = Facility
        fields = '__all__'


class RoomForm(StyledModelForm):
    class Meta:
        model = Room
        fields = [
            'number', 'name', 'room_type', 'custom_price', 'description',
            'facilities', 'status', 'image', 'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'facilities': forms.CheckboxSelectMultiple(),
        }


class ReservationAdminForm(StyledModelForm):
    rooms = forms.ModelMultipleChoiceField(
        label='Kamar',
        queryset=Room.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text='Pilih satu atau beberapa kamar dalam reservasi yang sama.',
    )

    class Meta:
        model = Reservation
        fields = ['customer', 'check_in', 'check_out', 'guests', 'notes', 'status', 'source']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date'}),
            'check_out': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rooms'].queryset = Room.objects.filter(is_active=True).exclude(
            status=Room.Status.MAINTENANCE
        ).select_related('room_type')
        if self.instance and self.instance.pk:
            room_ids = list(self.instance.reserved_rooms.values_list('room_id', flat=True))
            self.fields['rooms'].initial = room_ids or [self.instance.room_id]

    def clean(self):
        cleaned = super().clean()
        rooms = cleaned.get('rooms')
        check_in = cleaned.get('check_in')
        check_out = cleaned.get('check_out')
        guests = cleaned.get('guests')
        if check_in and check_out and check_out <= check_in:
            self.add_error('check_out', 'Tanggal check out harus setelah tanggal check in.')
        if rooms and guests:
            capacity = sum(room.room_type.capacity for room in rooms)
            if guests > capacity:
                self.add_error('guests', f'Kapasitas seluruh kamar maksimal {capacity} tamu.')
        if rooms and check_in and check_out and check_out > check_in:
            conflicts = [
                room for room in rooms
                if not room.is_available(
                    check_in,
                    check_out,
                    exclude_reservation=self.instance.pk if self.instance.pk else None,
                )
            ]
            if conflicts:
                self.add_error(
                    'rooms',
                    'Kamar tidak tersedia: ' + ', '.join(room.number for room in conflicts),
                )
        return cleaned


class PaymentAdminForm(StyledModelForm):
    class Meta:
        model = Payment
        fields = ['reservation', 'amount', 'proof', 'status', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}


class HotelSettingForm(StyledModelForm):
    class Meta:
        model = HotelSetting
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class UserAccountForm(forms.Form):
    first_name = forms.CharField(label='Nama depan', max_length=100)
    last_name = forms.CharField(label='Nama belakang', max_length=100, required=False)
    username = forms.CharField(label='Username', max_length=150)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='No. HP', max_length=30, required=False)
    nik = forms.CharField(label='NIK', max_length=16, required=False)
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'password-input'}),
        required=False,
        help_text='Wajib untuk akun baru; kosongkan jika tidak diubah.',
    )
    is_active = forms.BooleanField(label='Akun aktif', required=False, initial=True)

    def __init__(self, *args, instance=None, role='Customer', **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.role = role
        if role != 'Customer':
            self.fields.pop('nik')
        else:
            self.fields['nik'].required = True
            self.fields['nik'].help_text = 'NIK harus terdiri dari 16 digit.'
        if instance:
            self.fields['first_name'].initial = instance.first_name
            self.fields['last_name'].initial = instance.last_name
            self.fields['username'].initial = instance.username
            self.fields['email'].initial = instance.email
            self.fields['is_active'].initial = instance.is_active
            if role == 'Customer' and hasattr(instance, 'customer_profile'):
                self.fields['phone'].initial = instance.customer_profile.phone
                self.fields['nik'].initial = instance.customer_profile.nik
            elif role == 'Resepsionis' and hasattr(instance, 'receptionist_profile'):
                self.fields['phone'].initial = instance.receptionist_profile.phone

    def clean_username(self):
        qs = User.objects.filter(username__iexact=self.cleaned_data['username'])
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Username sudah digunakan.')
        return self.cleaned_data['username']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Email sudah digunakan.')
        return email

    def clean_nik(self):
        nik = ''.join(filter(str.isdigit, self.cleaned_data.get('nik') or ''))
        if self.role != 'Customer':
            return nik
        if len(nik) != 16:
            raise ValidationError('NIK harus terdiri dari tepat 16 digit angka.')
        qs = CustomerProfile.objects.filter(nik=nik)
        if self.instance and hasattr(self.instance, 'customer_profile'):
            qs = qs.exclude(pk=self.instance.customer_profile.pk)
        if qs.exists():
            raise ValidationError('NIK sudah digunakan akun lain.')
        return nik

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.instance and not password:
            raise ValidationError('Password wajib untuk akun baru.')
        if password:
            validate_password(password)
        return password

    def save(self):
        user = self.instance or User()
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.is_active = self.cleaned_data['is_active']
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        user.save()
        role_group, _ = Group.objects.get_or_create(name=self.role)
        user.groups.clear()
        user.groups.add(role_group)

        if self.role == 'Customer':
            profile, _ = CustomerProfile.objects.get_or_create(
                user=user,
                defaults={'phone': '', 'address': ''},
            )
            old_nik = profile.nik
            profile.phone = self.cleaned_data['phone']
            profile.nik = self.cleaned_data['nik']
            if old_nik != profile.nik:
                profile.identity_status = CustomerProfile.IdentityStatus.PENDING
                profile.identity_method = ''
                profile.identity_notes = ''
                profile.verified_by = None
                profile.verified_at = None
            profile.save()
        elif self.role == 'Resepsionis':
            profile, _ = ReceptionistProfile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data['phone']
            profile.is_active = user.is_active
            profile.save()
        return user
