from django import forms

from store.models import (Category, Language, Product, Coupon, ProductOffer, CategoryOffer)
from django.utils import timezone


class AdminLoginForm(forms.Form):

    email = forms.EmailField()

    password = forms.CharField(
        widget=forms.PasswordInput
    )


class CategoryForm(forms.ModelForm):

    class Meta:

        model = Category

        fields = [
            'name'
        ]

    def clean_name(self):

        name = self.cleaned_data.get(
            'name'
        ).strip()

        existing_category = Category.objects.filter(
            name__iexact=name
        )

        if self.instance.pk:

            existing_category = (
                existing_category.exclude(
                    pk=self.instance.pk
                )
            )

        if existing_category.exists():

            raise forms.ValidationError(
                'Category already exists.'
            )

        return name
    
class LanguageForm(forms.ModelForm):

    class Meta:

        model = Language

        fields = [
            'name'
        ]

    def clean_name(self):

        name = self.cleaned_data.get(
            'name'
        ).strip()

        existing_language = Language.objects.filter(
            name__iexact=name
        )

        if self.instance.pk:

            existing_language = (
                existing_language.exclude(
                    pk=self.instance.pk
                )
            )

        if existing_language.exists():

            raise forms.ValidationError(
                'Language already exists.'
            )

        return name
    
class ProductForm(forms.ModelForm):

    class Meta:

        model = Product

        fields = [
            'title',
            'category',
            'language',
            'author',
            'isbn',
            'publisher',
            'publication_date',
            'description',
            'cover_image',
            'regular_price',
            'sale_price',
            'stock',
            'is_featured',
        ]

        widgets = {

            'publication_date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'rows': 5
                }
            ),

        }

    def __init__(
        self,
        *args,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.fields[
            'category'
        ].queryset = (
            Category.objects.filter(
                is_active=True
            )
        )

        self.fields[
            'language'
        ].queryset = (
            Language.objects.filter(
                is_active=True
            )
        )

        if not self.instance.pk:

            self.fields[
                'cover_image'
            ].required = True

        for field_name, field in self.fields.items():

            field.widget.attrs.update({
                'class': 'form-control'
            })

        self.fields[
            'is_featured'
        ].widget.attrs.update({
            'class': 'form-check-input'
        })

    def clean_title(self):

        title = self.cleaned_data.get(
            'title'
        ).strip()

        if len(title) < 2:

            raise forms.ValidationError(
                'Title must contain at least 2 characters.'
            )

        return title

    def clean_author(self):

        author = self.cleaned_data.get(
            'author'
        ).strip()

        if len(author) < 2:

            raise forms.ValidationError(
                'Author name must contain at least 2 characters.'
            )

        return author

    def clean_publisher(self):

        publisher = self.cleaned_data.get(
            'publisher'
        ).strip()

        if len(publisher) < 2:

            raise forms.ValidationError(
                'Publisher name must contain at least 2 characters.'
            )

        return publisher

    def clean_description(self):

        description = self.cleaned_data.get(
            'description'
        ).strip()

        if len(description) < 20:

            raise forms.ValidationError(
                'Description must contain at least 20 characters.'
            )

        if len(description) > 3000:

            raise forms.ValidationError(
                'Description cannot exceed 3000 characters.'
            )

        return description

    def clean_isbn(self):

        isbn = self.cleaned_data.get(
            'isbn'
        ).strip()

        if len(isbn) < 10:

            raise forms.ValidationError(
                'ISBN must contain at least 10 characters.'
            )

        existing_product = Product.objects.filter(
            isbn=isbn
        )

        if self.instance.pk:

            existing_product = (
                existing_product.exclude(
                    pk=self.instance.pk
                )
            )

        if existing_product.exists():

            raise forms.ValidationError(
                'ISBN already exists.'
            )

        return isbn

    def clean_regular_price(self):

        regular_price = self.cleaned_data.get(
            'regular_price'
        )

        if regular_price <= 0:

            raise forms.ValidationError(
                'Regular price must be greater than zero.'
            )

        return regular_price

    def clean_sale_price(self):

        sale_price = self.cleaned_data.get(
            'sale_price'
        )

        if (
            sale_price is not None
            and sale_price <= 0
        ):

            raise forms.ValidationError(
                'Sale price must be greater than zero.'
            )

        return sale_price

    def clean_stock(self):

        stock = self.cleaned_data.get(
            'stock'
        )

        if stock < 0:

            raise forms.ValidationError(
                'Stock cannot be negative.'
            )

        return stock

    def clean(self):

        cleaned_data = super().clean()

        regular_price = cleaned_data.get(
            'regular_price'
        )

        sale_price = cleaned_data.get(
            'sale_price'
        )

        if (
            sale_price is not None
            and regular_price is not None
            and sale_price > regular_price
        ):

            raise forms.ValidationError(
                'Sale price cannot be greater than regular price.'
            )

        return cleaned_data
    

class ProductOfferForm(forms.ModelForm):

    class Meta:

        model = ProductOffer

        fields = [
            'product',
            'offer_percentage',
            'valid_from',
            'valid_to',
            'is_active'
        ]

        widgets = {

            'valid_from': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local'
                }
            ),

            'valid_to': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local'
                }
            )
        }

    def clean_offer_percentage(self):

        percentage = self.cleaned_data.get(
            'offer_percentage'
        )

        if percentage < 1 or percentage > 90:

            raise forms.ValidationError(
                'Offer must be between 1 and 90.'
            )

        return percentage

    def clean(self):

        cleaned_data = super().clean()

        valid_from = cleaned_data.get(
            'valid_from'
        )

        valid_to = cleaned_data.get(
            'valid_to'
        )

        if (

            valid_from
            and valid_to
            and valid_to <= valid_from

        ):

            raise forms.ValidationError(

                'End date must be greater than start date.'

            )

        return cleaned_data

class CategoryOfferForm(forms.ModelForm):

    class Meta:

        model = CategoryOffer

        fields = [
            'category',
            'offer_percentage',
            'valid_from',
            'valid_to',
            'is_active'
        ]

        widgets = {

            'valid_from': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local'
                }
            ),

            'valid_to': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local'
                }
            )
        }

    def clean_offer_percentage(self):

        percentage = self.cleaned_data.get(
            'offer_percentage'
        )

        if percentage < 1 or percentage > 90:

            raise forms.ValidationError(
                'Offer must be between 1 and 90.'
            )

        return percentage
    
    def clean(self):

        cleaned_data = super().clean()

        valid_from = cleaned_data.get(
            'valid_from'
        )

        valid_to = cleaned_data.get(
            'valid_to'
        )

        if (

            valid_from
            and valid_to
            and valid_to <= valid_from

        ):

            raise forms.ValidationError(

                'End date must be greater than start date.'

            )

        return cleaned_data


class CouponForm(forms.ModelForm):

    class Meta:

        model = Coupon

        fields = [

            'code',

            'discount_amount',

            'minimum_purchase_amount',

            'valid_from',

            'valid_to',

            'max_usage_per_user',

            'is_active',

        ]

        widgets = {

            'valid_from': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local'
                }
            ),

            'valid_to': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local'
                }
            ),

        }

    def __init__(
        self,
        *args,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        for field in self.fields.values():

            field.widget.attrs.update({
                'class': 'form-control'
            })

        self.fields[
            'is_active'
        ].widget.attrs.update({
            'class': 'form-check-input'
        })

        self.fields[
            'max_usage_per_user'
        ].label = (
            'Max Usage Per User'
        )

    def clean_code(self):

        code = self.cleaned_data[
            'code'
        ].strip().upper()

        existing_coupon = Coupon.objects.filter(
            code__iexact=code
        )

        if self.instance.pk:

            existing_coupon = (
                existing_coupon.exclude(
                    pk=self.instance.pk
                )
            )

        if existing_coupon.exists():

            raise forms.ValidationError(
                'Coupon code already exists.'
            )

        return code

    def clean_discount_amount(self):

        discount = self.cleaned_data[
            'discount_amount'
        ]

        if discount <= 0:

            raise forms.ValidationError(
                'Discount amount must be greater than zero.'
            )

        return discount

    def clean_minimum_purchase_amount(self):

        minimum_purchase = self.cleaned_data[
            'minimum_purchase_amount'
        ]

        if minimum_purchase < 0:

            raise forms.ValidationError(
                'Minimum purchase amount cannot be negative.'
            )

        return minimum_purchase

    def clean_max_usage_per_user(self):

        max_usage_per_user = self.cleaned_data[
            'max_usage_per_user'
        ]

        if max_usage_per_user <= 0:

            raise forms.ValidationError(
                'Maximum usage per user must be greater than zero.'
            )

        return max_usage_per_user

    def clean(self):

        cleaned_data = super().clean()

        valid_from = cleaned_data.get(
            'valid_from'
        )

        valid_to = cleaned_data.get(
            'valid_to'
        )

        discount_amount = cleaned_data.get(
            'discount_amount'
        )

        minimum_purchase_amount = cleaned_data.get(
            'minimum_purchase_amount'
        )

        now = timezone.now()

        if (
            valid_from
            and valid_to
            and valid_to <= valid_from
        ):

            raise forms.ValidationError(
                'Valid To must be later than Valid From.'
            )

        if (
            valid_to
            and valid_to < now
        ):

            raise forms.ValidationError(
                'Coupon expiry date cannot be in the past.'
            )

        if (
            discount_amount
            and minimum_purchase_amount
            and discount_amount > minimum_purchase_amount
        ):

            raise forms.ValidationError(
                'Discount amount cannot exceed minimum purchase amount.'
            )

        return cleaned_data