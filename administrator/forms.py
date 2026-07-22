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
        fields = ['number', 'name', 'room_type', 'custom_price', 'description', 'facilities', 'status', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'facilities': forms.CheckboxSelectMultiple(),
        }


class ReservationAdminForm(StyledModelForm):
    class Meta:
        model = Reservation
        fields = ['customer', 'room', 'check_in', 'check_out', 'guests', 'notes', 'status', 'source']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date'}),
            'check_out': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class PaymentAdminForm(StyledModelForm):
    class Meta:
        model = Payment
        fields = ['reservation', 'amount', 'proof', 'status', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}


class HotelSettingForm(StyledModelForm):
    class Meta:
        model = HotelSetting
        fields = '__all__'
        widgets = {'description': forms.Textarea(attrs={'rows': 4}), 'address': forms.Textarea(attrs={'rows': 3})}


class UserAccountForm(forms.Form):
    first_name = forms.CharField(label='Nama depan', max_length=100)
    last_name = forms.CharField(label='Nama belakang', max_length=100, required=False)
    username = forms.CharField(label='Username', max_length=150)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='No. HP', max_length=30, required=False)
    password = forms.CharField(label='Password', widget=forms.PasswordInput, required=False, help_text='Wajib untuk akun baru; kosongkan jika tidak diubah.')
    is_active = forms.BooleanField(label='Akun aktif', required=False, initial=True)

    def __init__(self, *args, instance=None, role='Customer', **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.role = role
        if instance:
            self.fields['first_name'].initial = instance.first_name
            self.fields['last_name'].initial = instance.last_name
            self.fields['username'].initial = instance.username
            self.fields['email'].initial = instance.email
            self.fields['is_active'].initial = instance.is_active
            if role == 'Customer' and hasattr(instance, 'customer_profile'):
                self.fields['phone'].initial = instance.customer_profile.phone
            if role == 'Resepsionis' and hasattr(instance, 'receptionist_profile'):
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
            profile, _ = CustomerProfile.objects.get_or_create(user=user, defaults={'phone': '', 'address': ''})
            profile.phone = self.cleaned_data['phone']
            profile.save()
        else:
            profile, _ = ReceptionistProfile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data['phone']
            profile.is_active = user.is_active
            profile.save()
        return user
