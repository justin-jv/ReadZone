import re

from django import forms

from .models import Address


class AddressForm(forms.ModelForm):

    class Meta:

        model = Address

        fields = [
            'address_label',
            'full_name',
            'mobile_number',
            'house_name',
            'area_street',
            'landmark',
            'city',
            'district',
            'state',
            'country',
            'pincode',
            'is_default'
        ]

    def clean_full_name(self):

        full_name = self.cleaned_data.get(
            'full_name'
        ).strip()

        pattern = r'^[A-Za-z\s\-]+$'

        if not re.match(pattern, full_name):

            raise forms.ValidationError(
                'Full name can contain only letters, spaces and hyphens.'
            )

        return full_name

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

        return mobile_number

    def clean_pincode(self):

        pincode = self.cleaned_data.get(
            'pincode'
        )

        if not pincode.isdigit():

            raise forms.ValidationError(
                'Pincode must contain only digits.'
            )

        if len(pincode) != 6:

            raise forms.ValidationError(
                'Pincode must contain exactly 6 digits.'
            )

        return pincode