from pathlib import Path

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from administrator.models import Payment, Reservation, Room
from .models import CustomerProfile
from django.utils import timezone



class LoginForm(forms.Form):
    username = forms.CharField(label="Username atau Email")
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
    )


class RegistrationForm(forms.Form):
    name = forms.CharField(
        label="Nama Lengkap",
        max_length=150,
    )

    email = forms.EmailField(
        label="Email",
    )

    phone = forms.CharField(
        label="No. HP",
        max_length=30,
    )

    address = forms.CharField(
        label="Alamat",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    nik = forms.CharField(
        label="NIK",
        max_length=16,
        min_length=16,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Masukkan 16 digit NIK"
            }
        ),
    )

    is_married = forms.BooleanField(
        label="Sudah Menikah",
        required=False,
        help_text="Centang jika sudah menikah.",
    )

    marriage_certificate = forms.FileField(
        label="Bukti Surat Nikah",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".pdf,.jpg,.jpeg,.png"
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
    )

    password_confirm = forms.CharField(
        label="Konfirmasi Password",
        widget=forms.PasswordInput,
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email sudah digunakan.")

        return email

    def clean_nik(self):
        nik = "".join(
            filter(
                str.isdigit,
                self.cleaned_data["nik"],
            )
        )

        if len(nik) != 16:
            raise ValidationError(
                "NIK harus terdiri dari 16 digit."
            )

        if CustomerProfile.objects.filter(
            nik=nik
        ).exists():
            raise ValidationError(
                "NIK sudah terdaftar."
            )

        return nik

    def clean_marriage_certificate(self):
        file = self.cleaned_data.get(
            "marriage_certificate"
        )

        if not file:
            return file

        if file.size > 5 * 1024 * 1024:
            raise ValidationError(
                "Ukuran file maksimal 5 MB."
            )

        allowed = {
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
        }

        if Path(file.name).suffix.lower() not in allowed:
            raise ValidationError(
                "File harus berupa PDF, JPG, JPEG, atau PNG."
            )

        return file

    def clean(self):
        cleaned = super().clean()

        password = cleaned.get("password")
        password_confirm = cleaned.get(
            "password_confirm"
        )

        if (
            password
            and password_confirm
            and password != password_confirm
        ):
            self.add_error(
                "password_confirm",
                "Konfirmasi password tidak sama.",
            )

        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error(
                    "password",
                    exc,
                )

        if (
            cleaned.get("is_married")
            and not cleaned.get(
                "marriage_certificate"
            )
        ):
            self.add_error(
                "marriage_certificate",
                "Bukti surat nikah wajib diunggah.",
            )

        return cleaned

class CustomerProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nama Depan",
        max_length=100,
    )

    last_name = forms.CharField(
        label="Nama Belakang",
        max_length=100,
        required=False,
    )

    email = forms.EmailField(
        label="Email",
    )

    class Meta:
        model = CustomerProfile
        fields = [
            "phone",
            "address",
        ]
        widgets = {
            "address": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if (
            User.objects.exclude(pk=self.user.pk)
            .filter(email__iexact=email)
            .exists()
        ):
            raise ValidationError(
                "Email sudah digunakan."
            )

        return email

    def save(self, commit=True):
        profile = super().save(commit=False)

        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.email = self.cleaned_data["email"]

        if commit:
            self.user.save()
            profile.save()

        return profile

class ReservationForm(forms.ModelForm):
    rooms = forms.ModelMultipleChoiceField(
        label="Pilih Kamar",
        queryset=Room.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            "Anda dapat memilih satu atau beberapa kamar "
            "dalam satu reservasi."
        ),
    )

    class Meta:
        model = Reservation
        fields = [
            "check_in",
            "check_out",
            "guests",
            "notes",
        ]

        widgets = {
            "check_in": forms.DateInput(
                attrs={"type": "date"}
            ),
            "check_out": forms.DateInput(
                attrs={"type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

    def __init__(
        self,
        *args,
        room=None,
        instance=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            instance=instance,
            **kwargs,
        )

        queryset = (
            Room.objects.filter(is_active=True)
            .exclude(status=Room.Status.MAINTENANCE)
            .select_related("room_type")
        )

        self.fields["rooms"].queryset = queryset

        if room:
            self.fields["rooms"].initial = [room]

        elif instance and instance.pk:
            selected = instance.reserved_rooms.values_list(
                "room_id",
                flat=True,
            )

            self.fields["rooms"].initial = (
                list(selected)
                or [instance.room_id]
            )

    def clean_check_in(self):
        check_in = self.cleaned_data["check_in"]

        if check_in < timezone.localdate():
            raise ValidationError(
                "Tanggal check in tidak boleh sebelum hari ini."
            )

        return check_in

    def clean(self):
        cleaned = super().clean()

        rooms = cleaned.get("rooms")
        check_in = cleaned.get("check_in")
        check_out = cleaned.get("check_out")
        guests = cleaned.get("guests")

        if (
            check_in
            and check_out
            and check_out <= check_in
        ):
            self.add_error(
                "check_out",
                "Tanggal check out harus setelah check in.",
            )

            return cleaned

        if rooms and guests:
            capacity = sum(
                room.room_type.capacity
                for room in rooms
            )

            if guests > capacity:
                self.add_error(
                    "guests",
                    f"Jumlah tamu maksimal adalah {capacity} orang.",
                )

        if (
            rooms
            and check_in
            and check_out
        ):
            unavailable = []

            for room in rooms:
                if not room.is_available(
                    check_in=check_in,
                    check_out=check_out,
                    exclude_reservation=(self.instance.pk
                                         if self.instance and self.instance.pk
                                         else None),
                                         ):
                    unavailable.append(room)

            if unavailable:
                labels = ", ".join(
                    f"{room.number} - {room.name}"
                    for room in unavailable
                )

                self.add_error(
                    "rooms",
                    f"Kamar berikut tidak tersedia: {labels}",
                )

        return cleaned

class PaymentUploadForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "proof",
        ]
        widgets = {
            "proof": forms.ClearableFileInput(
                attrs={
                    "accept": "image/*",
                }
            ),
        }

    def clean_proof(self):
        proof = self.cleaned_data.get("proof")

        if not proof:
            raise ValidationError(
                "Bukti pembayaran wajib diunggah."
            )

        if proof.size > 5 * 1024 * 1024:
            raise ValidationError(
                "Ukuran file maksimal 5 MB."
            )

        allowed = {
            ".jpg",
            ".jpeg",
            ".png",
            ".pdf",
        }

        suffix = Path(proof.name).suffix.lower()

        if suffix not in allowed:
            raise ValidationError(
                "File harus berupa JPG, JPEG, PNG, atau PDF."
            )

        return proof