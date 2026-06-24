import re

from django import forms

from .models import CustomUser


class SignupForm(forms.Form):

    first_name = forms.CharField(
        max_length=100
    )

    last_name = forms.CharField(
        max_length=100
    )

    email = forms.EmailField()

    mobile_number = forms.CharField(
        max_length=10
    )

    password = forms.CharField(
        widget=forms.PasswordInput
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput
    )

    def clean_first_name(self):

        first_name = self.cleaned_data.get('first_name').strip()

        pattern = r'^[A-Za-z\s\-]+$'

        if not re.match(pattern, first_name):
            raise forms.ValidationError(
                "First name can contain only letters, spaces and hyphens."
            )

        return first_name

    def clean_last_name(self):

        last_name = self.cleaned_data.get('last_name').strip()

        pattern = r'^[A-Za-z\s\-]+$'

        if not re.match(pattern, last_name):
            raise forms.ValidationError(
                "Last name can contain only letters, spaces and hyphens."
            )

        return last_name

    def clean_email(self):

        email = self.cleaned_data.get('email').lower()

        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean_mobile_number(self):

        mobile_number = self.cleaned_data.get('mobile_number')

        if not mobile_number.isdigit():
            raise forms.ValidationError(
                "Mobile number must contain only digits."
            )

        if len(mobile_number) != 10:
            raise forms.ValidationError(
                "Mobile number must contain exactly 10 digits."
            )

        if CustomUser.objects.filter(
            mobile_number=mobile_number
        ).exists():
            raise forms.ValidationError(
                "This mobile number is already registered."
            )

        return mobile_number

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:

            if password != confirm_password:
                raise forms.ValidationError(
                    "Passwords do not match."
                )

            password_pattern = (
                r'^(?=.*[a-z])'
                r'(?=.*[A-Z])'
                r'(?=.*\d)'
                r'(?=.*[@$!%*?&])'
                r'[A-Za-z\d@$!%*?&]{8,}$'
            )

            if not re.match(password_pattern, password):
                raise forms.ValidationError(
                    "Password must contain at least "
                    "8 characters, one uppercase letter, "
                    "one lowercase letter, one digit "
                    "and one special character."
                )

        return cleaned_data
    
class OTPVerificationForm(forms.Form):

    otp = forms.CharField(
        max_length=6,
        min_length=6
    )

class LoginForm(forms.Form):

    email = forms.EmailField()

    password = forms.CharField(
        widget=forms.PasswordInput
    )

class ForgotPasswordForm(forms.Form):

    email = forms.EmailField()

    def clean_email(self):

        email = self.cleaned_data.get('email').lower()

        if not CustomUser.objects.filter(
            email=email
        ).exists():

            raise forms.ValidationError(
                "No account found with this email."
            )

        return email


class ResetPasswordForm(forms.Form):

    password = forms.CharField(
        widget=forms.PasswordInput
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput
    )

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:

            if password != confirm_password:

                raise forms.ValidationError(
                    "Passwords do not match."
                )

            password_pattern = (
                r'^(?=.*[a-z])'
                r'(?=.*[A-Z])'
                r'(?=.*\d)'
                r'(?=.*[@$!%*?&])'
                r'[A-Za-z\d@$!%*?&]{8,}$'
            )

            if not re.match(
                password_pattern,
                password
            ):
                raise forms.ValidationError(
                    "Password must contain at least "
                    "8 characters, one uppercase "
                    "letter, one lowercase letter, "
                    "one digit and one special "
                    "character."
                )

        return cleaned_data
    
class EditProfileForm(forms.ModelForm):

    class Meta:

        model = CustomUser

        fields = [
            'first_name',
            'last_name',
            'mobile_number',
            'profile_image'
        ]

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop('user')

        super().__init__(*args, **kwargs)

    def clean_first_name(self):

        first_name = self.cleaned_data.get(
            'first_name'
        ).strip()

        pattern = r'^[A-Za-z\s\-]+$'

        if not re.match(pattern, first_name):

            raise forms.ValidationError(
                'First name can contain only letters, spaces and hyphens.'
            )

        return first_name

    def clean_last_name(self):

        last_name = self.cleaned_data.get(
            'last_name'
        ).strip()

        pattern = r'^[A-Za-z\s\-]+$'

        if not re.match(pattern, last_name):

            raise forms.ValidationError(
                'Last name can contain only letters, spaces and hyphens.'
            )

        return last_name

    def clean_mobile_number(self):

        mobile_number = self.cleaned_data.get(
            'mobile_number'
        )

        if not mobile_number.isdigit():

            raise forms.ValidationError(
                'Mobile number must contain only digits.'
            )

        if len(mobile_number) != 10:

            raise forms.ValidationError(
                'Mobile number must contain exactly 10 digits.'
            )

        existing_user = CustomUser.objects.filter(
            mobile_number=mobile_number
        ).exclude(
            id=self.user.id
        )

        if existing_user.exists():

            raise forms.ValidationError(
                'This mobile number is already registered.'
            )

        return mobile_number
    
class ChangePasswordForm(forms.Form):

    current_password = forms.CharField(
        widget=forms.PasswordInput
    )

    new_password = forms.CharField(
        widget=forms.PasswordInput
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput
    )

    def clean(self):

        cleaned_data = super().clean()

        new_password = cleaned_data.get(
            'new_password'
        )

        confirm_password = cleaned_data.get(
            'confirm_password'
        )

        if new_password and confirm_password:

            if new_password != confirm_password:

                raise forms.ValidationError(
                    "Passwords do not match."
                )

            password_pattern = (
                r'^(?=.*[a-z])'
                r'(?=.*[A-Z])'
                r'(?=.*\d)'
                r'(?=.*[@$!%*?&])'
                r'[A-Za-z\d@$!%*?&]{8,}$'
            )

            if not re.match(
                password_pattern,
                new_password
            ):
                raise forms.ValidationError(
                    "Password must contain at least "
                    "8 characters, one uppercase letter, "
                    "one lowercase letter, one digit "
                    "and one special character."
                )

        return cleaned_data
    
class ChangeEmailForm(forms.Form):

    new_email = forms.EmailField()

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop('user')

        super().__init__(*args, **kwargs)

    def clean_new_email(self):

        new_email = self.cleaned_data.get(
            'new_email'
        ).lower()

        if new_email == self.user.email:

            raise forms.ValidationError(
                'New email cannot be the same as your current email.'
            )

        if CustomUser.objects.filter(
            email=new_email
        ).exists():

            raise forms.ValidationError(
                'This email is already registered.'
            )

        return new_email