from django import forms
from django.contrib.auth.models import Group, User
from customer.models import CustomerProfile
from administrator.models import Payment, Reservation, Room


class WalkInReservationForm(forms.ModelForm):
    customer_name = forms.CharField(label='Nama customer', max_length=150)
    customer_email = forms.EmailField(label='Email customer')
    customer_phone = forms.CharField(label='No. HP customer', max_length=30)
    customer_address = forms.CharField(label='Alamat', widget=forms.Textarea(attrs={'rows': 2}), required=False)

    class Meta:
        model = Reservation
        fields = ['room', 'check_in', 'check_out', 'guests', 'notes']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date'}),
            'check_out': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].queryset = Room.objects.filter(is_active=True).exclude(status=Room.Status.MAINTENANCE)

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
            user = User.objects.create_user(username=username, email=email, first_name=names[0], last_name=names[1] if len(names) > 1 else '')
            user.set_unusable_password()
            user.save()
            group, _ = Group.objects.get_or_create(name='Customer')
            user.groups.add(group)
        profile, _ = CustomerProfile.objects.get_or_create(user=user, defaults={'phone': '', 'address': ''})
        profile.phone = self.cleaned_data['customer_phone']
        profile.address = self.cleaned_data['customer_address']
        profile.save()
        return user


class PaymentVerificationForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['status', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}
