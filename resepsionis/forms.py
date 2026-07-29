from pathlib import Path

from django import forms
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError

from administrator.models import Payment, Reservation, Room
from customer.models import CustomerProfile


class WalkInReservationForm(forms.ModelForm):
    customer_name = forms.CharField(label='Nama customer', max_length=150)
    customer_nik = forms.CharField(label='NIK customer', max_length=16, min_length=16)
    customer_email = forms.EmailField(label='Email customer')
    customer_phone = forms.CharField(label='No. HP customer', max_length=30)
    customer_address = forms.CharField(
        label='Alamat',
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
    )
    is_married = forms.BooleanField(label='Sudah menikah', required=False)
    marriage_certificate = forms.FileField(
        label='Bukti surat nikah',
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
    )
    rooms = forms.ModelMultipleChoiceField(
        label='Kamar',
        queryset=Room.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text='Pilih satu atau beberapa kamar.',
    )

    class Meta:
        model = Reservation
        fields = ['check_in', 'check_out', 'guests', 'notes']
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

    def clean_customer_nik(self):
        nik = ''.join(filter(str.isdigit, self.cleaned_data['customer_nik']))
        if len(nik) != 16:
            raise ValidationError('NIK harus terdiri dari tepat 16 digit.')
        email = (self.data.get('customer_email') or '').lower()
        existing = CustomerProfile.objects.filter(nik=nik).select_related('user').first()
        if existing and existing.user.email.lower() != email:
            raise ValidationError('NIK sudah digunakan oleh akun dengan email lain.')
        return nik

    def clean_marriage_certificate(self):
        uploaded = self.cleaned_data.get('marriage_certificate')
        if not uploaded:
            return uploaded
        if uploaded.size > 5 * 1024 * 1024:
            raise ValidationError('Ukuran bukti surat nikah maksimal 5 MB.')
        if Path(uploaded.name).suffix.lower() not in {'.pdf', '.jpg', '.jpeg', '.png'}:
            raise ValidationError('Format bukti surat nikah harus PDF, JPG, JPEG, atau PNG.')
        return uploaded

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('is_married') and not cleaned.get('marriage_certificate'):
            email = (cleaned.get('customer_email') or '').lower()
            existing = User.objects.filter(email__iexact=email).first()
            existing_certificate = bool(
                existing
                and hasattr(existing, 'customer_profile')
                and existing.customer_profile.marriage_certificate
            )
            if not existing_certificate:
                self.add_error('marriage_certificate', 'Surat nikah wajib untuk customer yang sudah menikah.')

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
            conflicts = [room for room in rooms if not room.is_available(check_in, check_out)]
            if conflicts:
                self.add_error('rooms', 'Kamar tidak tersedia: ' + ', '.join(r.number for r in conflicts))
        return cleaned

    def get_or_create_customer(self):
        email = self.cleaned_data['customer_email'].lower()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            base = email.split('@')[0].replace('.', '_')[:120] or 'customer'
            username = base
            i = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'
                i += 1
            names = self.cleaned_data['customer_name'].strip().split(maxsplit=1)
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=names[0],
                last_name=names[1] if len(names) > 1 else '',
            )
            user.set_unusable_password()
            user.save()
            group, _ = Group.objects.get_or_create(name='Customer')
            user.groups.add(group)
        profile, _ = CustomerProfile.objects.get_or_create(
            user=user,
            defaults={'phone': '', 'address': ''},
        )
        old_nik = profile.nik
        old_married = profile.is_married
        old_certificate = getattr(profile.marriage_certificate, 'name', '') or ''

        profile.phone = self.cleaned_data['customer_phone']
        profile.address = self.cleaned_data['customer_address']
        profile.nik = self.cleaned_data['customer_nik']
        profile.is_married = self.cleaned_data['is_married']
        if self.cleaned_data.get('marriage_certificate'):
            profile.marriage_certificate = self.cleaned_data['marriage_certificate']
        elif not profile.is_married:
            profile.marriage_certificate = None

        new_certificate = getattr(profile.marriage_certificate, 'name', '') or ''
        if (
            old_nik != profile.nik
            or bool(old_married) != bool(profile.is_married)
            or old_certificate != new_certificate
        ):
            profile.identity_status = CustomerProfile.IdentityStatus.PENDING
            profile.identity_method = ''
            profile.identity_notes = ''
            profile.verified_by = None
            profile.verified_at = None
        profile.save()
        return user


class PaymentVerificationForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['status', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}


class KeyReturnForm(forms.Form):
    status = forms.ChoiceField(
        label='Kondisi pengembalian kunci',
        choices=[('RETURNED', 'Kunci dikembalikan'), ('PROBLEM', 'Kunci hilang/bermasalah')],
    )
    notes = forms.CharField(
        label='Catatan kondisi kunci',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )


class IdentityValidationForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ['identity_status', 'identity_method', 'identity_notes']
        widgets = {'identity_notes': forms.Textarea(attrs={'rows': 4})}

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('identity_status')
        method = cleaned.get('identity_method')
        notes = (cleaned.get('identity_notes') or '').strip()

        if status in [CustomerProfile.IdentityStatus.VERIFIED, CustomerProfile.IdentityStatus.REJECTED] and not method:
            self.add_error('identity_method', 'Pilih metode pemeriksaan identitas.')

        if status == CustomerProfile.IdentityStatus.VERIFIED:
            nik = ''.join(filter(str.isdigit, self.instance.nik or ''))
            if len(nik) != 16:
                raise forms.ValidationError('Identitas belum dapat disetujui karena NIK belum berisi 16 digit.')
            if self.instance.is_married and not self.instance.marriage_certificate:
                raise forms.ValidationError(
                    'Identitas belum dapat disetujui karena bukti surat nikah belum tersedia.'
                )

        if status == CustomerProfile.IdentityStatus.REJECTED and not notes:
            self.add_error('identity_notes', 'Alasan penolakan wajib diisi.')
        return cleaned


class KtpGuaranteeForm(forms.Form):
    notes = forms.CharField(
        label='Catatan jaminan KTP',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
