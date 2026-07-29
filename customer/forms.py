from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from administrator.models import Payment, Reservation, Room
from .models import CustomerProfile


class LoginForm(forms.Form):
    username = forms.CharField(label='Username atau Email')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)


class RegistrationForm(forms.Form):
    name = forms.CharField(label='Nama lengkap', max_length=150)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='No. HP', max_length=30)
    address = forms.CharField(label='Alamat', widget=forms.Textarea(attrs={'rows': 3}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password_confirm = forms.CharField(label='Konfirmasi password', widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email sudah digunakan.')
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        if password and password != cleaned.get('password_confirm'):
            self.add_error('password_confirm', 'Konfirmasi password tidak sama.')
        if password:
            validate_password(password)
        return cleaned


class CustomerProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='Nama depan', max_length=100)
    last_name = forms.CharField(label='Nama belakang', max_length=100, required=False)
    email = forms.EmailField(label='Email')

    class Meta:
        model = CustomerProfile
        fields = ['phone', 'address']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise ValidationError('Email sudah digunakan.')
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        if commit:
            self.user.save()
            profile.save()
        return profile


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['room', 'check_in', 'check_out', 'guests', 'notes']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date'}),
            'check_out': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, room=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].queryset = Room.objects.filter(is_active=True).exclude(status=Room.Status.MAINTENANCE)
        if room:
            self.fields['room'].initial = room

    def clean_check_in(self):
        value = self.cleaned_data['check_in']
        if value < timezone.localdate():
            raise ValidationError('Tanggal check in tidak boleh sebelum hari ini.')
        return value


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
