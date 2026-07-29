from pathlib import Path

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from administrator.models import Payment, Reservation, Room
from .models import CustomerProfile


PASSWORD_ATTRS = {
    'class': 'password-input',
    'autocomplete': 'current-password',
}


class LoginForm(forms.Form):
    username = forms.CharField(label='Username atau Email')
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs=PASSWORD_ATTRS),
    )


class RegistrationForm(forms.Form):
    name = forms.CharField(label='Nama lengkap', max_length=150)
    nik = forms.CharField(
        label='NIK',
        max_length=16,
        min_length=16,
        help_text='Masukkan 16 digit NIK sesuai KTP.',
    )
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='No. HP', max_length=30)
    address = forms.CharField(label='Alamat', widget=forms.Textarea(attrs={'rows': 3}))
    is_married = forms.BooleanField(
        label='Sudah menikah',
        required=False,
        help_text='Centang jika sudah menikah. Bukti surat nikah wajib diunggah.',
    )
    marriage_certificate = forms.FileField(
        label='Bukti surat nikah',
        required=False,
        help_text='Format PDF/JPG/PNG, maksimal 5 MB.',
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={**PASSWORD_ATTRS, 'autocomplete': 'new-password'}),
    )
    password_confirm = forms.CharField(
        label='Konfirmasi password',
        widget=forms.PasswordInput(attrs={**PASSWORD_ATTRS, 'autocomplete': 'new-password'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email sudah digunakan.')
        return email

    def clean_nik(self):
        nik = ''.join(filter(str.isdigit, self.cleaned_data['nik']))
        if len(nik) != 16:
            raise ValidationError('NIK harus terdiri dari tepat 16 digit angka.')
        if CustomerProfile.objects.filter(nik=nik).exists():
            raise ValidationError('NIK sudah terdaftar pada akun lain.')
        return nik

    def clean_marriage_certificate(self):
        file = self.cleaned_data.get('marriage_certificate')
        if not file:
            return file
        if file.size > 5 * 1024 * 1024:
            raise ValidationError('Ukuran bukti surat nikah maksimal 5 MB.')
        allowed = {'.pdf', '.jpg', '.jpeg', '.png'}
        if Path(file.name).suffix.lower() not in allowed:
            raise ValidationError('Format bukti surat nikah harus PDF, JPG, JPEG, atau PNG.')
        return file

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        if password and password != cleaned.get('password_confirm'):
            self.add_error('password_confirm', 'Konfirmasi password tidak sama.')
        if password:
            validate_password(password)
        if cleaned.get('is_married') and not cleaned.get('marriage_certificate'):
            self.add_error('marriage_certificate', 'Bukti surat nikah wajib bagi pengguna yang sudah menikah.')
        return cleaned


class CustomerProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='Nama depan', max_length=100)
    last_name = forms.CharField(label='Nama belakang', max_length=100, required=False)
    email = forms.EmailField(label='Email')

    class Meta:
        model = CustomerProfile
        fields = ['nik', 'phone', 'address', 'is_married', 'marriage_certificate']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'marriage_certificate': forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
        self.fields['marriage_certificate'].help_text = 'Format PDF/JPG/PNG, maksimal 5 MB.'
        if self.instance and self.instance.identity_is_verified:
            self.fields['nik'].disabled = True
            self.fields['nik'].help_text = 'NIK sudah terverifikasi dan tidak dapat diubah.'

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise ValidationError('Email sudah digunakan.')
        return email

    def clean_nik(self):
        nik = ''.join(filter(str.isdigit, self.cleaned_data.get('nik') or ''))
        if len(nik) != 16:
            raise ValidationError('NIK harus terdiri dari tepat 16 digit angka.')
        qs = CustomerProfile.objects.filter(nik=nik).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('NIK sudah digunakan akun lain.')
        return nik

    def clean_marriage_certificate(self):
        uploaded = self.cleaned_data.get('marriage_certificate')
        if not uploaded or uploaded is False:
            return uploaded
        if uploaded.size > 5 * 1024 * 1024:
            raise ValidationError('Ukuran bukti surat nikah maksimal 5 MB.')
        if Path(uploaded.name).suffix.lower() not in {'.pdf', '.jpg', '.jpeg', '.png'}:
            raise ValidationError('Format bukti surat nikah harus PDF, JPG, JPEG, atau PNG.')
        return uploaded

    def clean(self):
        cleaned = super().clean()
        uploaded = cleaned.get('marriage_certificate')
        existing_file = bool(self.instance and self.instance.marriage_certificate)
        clear_requested = uploaded is False
        has_certificate = bool(uploaded) or (existing_file and not clear_requested)
        if cleaned.get('is_married') and not has_certificate:
            self.add_error('marriage_certificate', 'Bukti surat nikah wajib bagi pengguna yang sudah menikah.')
        return cleaned

    def save(self, commit=True):
        old = CustomerProfile.objects.filter(pk=self.instance.pk).values(
            'nik', 'is_married', 'marriage_certificate'
        ).first() or {}
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']

        if not profile.is_married:
            profile.marriage_certificate = None

        new_certificate = getattr(profile.marriage_certificate, 'name', '') or ''
        identity_data_changed = any([
            old.get('nik') != profile.nik,
            bool(old.get('is_married')) != bool(profile.is_married),
            (old.get('marriage_certificate') or '') != new_certificate,
        ])
        if identity_data_changed:
            profile.identity_status = CustomerProfile.IdentityStatus.PENDING
            profile.identity_method = ''
            profile.verified_by = None
            profile.verified_at = None
            profile.identity_notes = ''

        if commit:
            self.user.save()
            profile.save()
        return profile


class ReservationForm(forms.ModelForm):
    rooms = forms.ModelMultipleChoiceField(
        label='Pilih kamar',
        queryset=Room.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text='Anda dapat memilih satu atau beberapa kamar dalam satu reservasi.',
    )
    class Meta:
        model = Reservation
        fields = ['check_in', 'check_out', 'guests', 'notes']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date'}),
            'check_out': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, room=None, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        queryset = Room.objects.filter(is_active=True).exclude(
            status=Room.Status.MAINTENANCE
        ).select_related('room_type')
        self.fields['rooms'].queryset = queryset
        if room:
            self.fields['rooms'].initial = [room]
        elif instance and instance.pk:
            selected = instance.reserved_rooms.values_list('room_id', flat=True)
            self.fields['rooms'].initial = list(selected) or [instance.room_id]

    def clean_check_in(self):
        value = self.cleaned_data['check_in']
        if value < timezone.localdate():
            raise ValidationError('Tanggal check in tidak boleh sebelum hari ini.')
        return value

    def clean(self):
        cleaned = super().clean()
        rooms = cleaned.get('rooms')
        check_in = cleaned.get('check_in')
        check_out = cleaned.get('check_out')
        guests = cleaned.get('guests')

        if check_in and check_out and check_out <= check_in:
            self.add_error('check_out', 'Tanggal check out harus setelah tanggal check in.')
            return cleaned

        if rooms and guests:
            capacity = sum(room.room_type.capacity for room in rooms)
            if guests > capacity:
                self.add_error('guests', f'Jumlah tamu maksimal untuk kamar yang dipilih adalah {capacity} orang.')

        if rooms and check_in and check_out and check_out > check_in:
            unavailable = [
                room for room in rooms
                if not room.is_available(
                    check_in=check_in,
                    check_out=check_out,
                    exclude_reservation=self.instance.pk if self.instance else None,
                )
            ]
            if unavailable:
                labels = ', '.join(f'{room.number} - {room.name}' for room in unavailable)
                self.add_error('rooms', f'Kamar berikut sudah dipesan pada tanggal tersebut: {labels}.')
        return cleaned


class PaymentUploadForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['proof']
        widgets = {'proof': forms.ClearableFileInput(attrs={'accept': 'image/*'})}

    def clean_proof(self):
        proof = self.cleaned_data.get('proof')
        if not proof:
            raise ValidationError('Bukti pembayaran wajib diunggah.')
        if proof.size > 5 * 1024 * 1024:
            raise ValidationError('Ukuran file maksimal 5 MB.')
        return proof
