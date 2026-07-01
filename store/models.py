from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from decimal import Decimal
from django.utils import timezone

from accounts.models import CustomUser


class Address(models.Model):

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='addresses'
    )

    address_label = models.CharField(
        max_length=100
    )

    full_name = models.CharField(
        max_length=100
    )

    mobile_number = models.CharField(
        max_length=10
    )

    house_name = models.CharField(
        max_length=255
    )

    area_street = models.CharField(
        max_length=255
    )

    landmark = models.CharField(
        max_length=255,
        blank=True
    )

    city = models.CharField(
        max_length=100
    )

    district = models.CharField(
        max_length=100
    )

    state = models.CharField(
        max_length=100
    )

    country = models.CharField(
        max_length=100
    )

    pincode = models.CharField(
        max_length=10
    )

    is_default = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return (
            f"{self.full_name} "
            f"({self.address_label})"
        )

    def save(self, *args, **kwargs):

        if self.is_default:

            Address.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(
                pk=self.pk
            ).update(
                is_default=False
            )

        super().save(*args, **kwargs)


class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return self.name


class Language(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return self.name


class Product(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )

    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name='products'
    )

    title = models.CharField(
        max_length=255
    )

    slug = models.SlugField(
        max_length=500,
        unique=True,
        blank=True
    )

    author = models.CharField(
        max_length=255
    )

    isbn = models.CharField(
        max_length=20,
        unique=True
    )

    publisher = models.CharField(
        max_length=255
    )

    publication_date = models.DateField()

    description = models.TextField()

    cover_image = models.ImageField(
        upload_to='products/covers/',
        blank=True,
        null=True
    )

    regular_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    stock = models.PositiveIntegerField(
        default=0
    )

    sales_count = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    is_featured = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):

        if (
            self.sale_price is not None
            and self.sale_price > self.regular_price
        ):

            raise ValidationError(
                'Sale price cannot be greater than regular price.'
            )

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = slugify(
                f"{self.title}-{self.isbn}"
            )

        super().save(*args, **kwargs)

    def __str__(self):

        return self.title
    
    @property
    def effective_price(self):

        base_price = (
            self.sale_price
            if self.sale_price
            else self.regular_price
        )

        now = timezone.now()

        product_offer = ProductOffer.objects.filter(

            product=self,

            is_active=True,

            valid_from__lte=now,

            valid_to__gte=now

        ).order_by(
            '-offer_percentage'
        ).first()

        category_offer = CategoryOffer.objects.filter(

            category=self.category,

            is_active=True,

            valid_from__lte=now,

            valid_to__gte=now

        ).order_by(
            '-offer_percentage'
        ).first()

        product_percentage = (
            product_offer.offer_percentage
            if product_offer
            else 0
        )

        category_percentage = (
            category_offer.offer_percentage
            if category_offer
            else 0
        )

        best_offer = max(

            product_percentage,

            category_percentage

        )

        if best_offer:

            discount_amount = (

                base_price
                * best_offer
            ) / 100

            return (
                base_price
                - discount_amount
            )

        return base_price
    
    @property
    def best_offer_percentage(self):

        now = timezone.now()

        product_offer = ProductOffer.objects.filter(

            product=self,

            is_active=True,

            valid_from__lte=now,

            valid_to__gte=now

        ).order_by(
            '-offer_percentage'
        ).first()

        category_offer = CategoryOffer.objects.filter(

            category=self.category,

            is_active=True,

            valid_from__lte=now,

            valid_to__gte=now

        ).order_by(
            '-offer_percentage'
        ).first()

        return max(

            product_offer.offer_percentage
            if product_offer else 0,

            category_offer.offer_percentage
            if category_offer else 0

        )

    @property
    def discount_percentage(self):
        if (
            self.sale_price
            and self.sale_price < self.regular_price
        ):
            return round(
                (
                    (self.regular_price - self.sale_price)
                    / self.regular_price
                ) * 100
            )
        return 0


class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image = models.ImageField(
        upload_to='products/'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"{self.product.title} Image"
        )
    
class Wishlist(models.Model):

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = (
            'user',
            'product'
        )

    def __str__(self):

        return (
            f"{self.user.email} - "
            f"{self.product.title}"
        )
    
class Cart(models.Model):

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='cart'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return (
            f"{self.user.email} Cart"
        )


class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = (
            'cart',
            'product'
        )

    def __str__(self):

        return (
            f"{self.product.title}"
        )

    @property
    def subtotal(self):

        return (
            self.product.effective_price
            * self.quantity
        )       

class Order(models.Model):

    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
        ('wallet', 'Wallet'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    )

    ORDER_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('partially_cancelled', 'Partially Cancelled'),
        ('cancelled', 'Cancelled'),
    )

    order_id = models.CharField(
        max_length=20,
        unique=True
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    full_name = models.CharField(
        max_length=100
    )

    mobile_number = models.CharField(
        max_length=10
    )

    house_name = models.CharField(
        max_length=255
    )

    area_street = models.CharField(
        max_length=255
    )

    landmark = models.CharField(
        max_length=255,
        blank=True
    )

    city = models.CharField(
        max_length=100
    )

    district = models.CharField(
        max_length=100
    )

    state = models.CharField(
        max_length=100
    )

    country = models.CharField(
        max_length=100
    )

    pincode = models.CharField(
        max_length=10
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    shipping_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    coupon_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cod'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )

    razorpay_order_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    razorpay_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    razorpay_signature = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    order_status = models.CharField(
        max_length=30,
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return self.order_id

    @property
    def total_books(self):

        return sum(
            item.quantity
            for item in self.items.all()
        )   

class OrderItem(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('return_requested', 'Return Requested'),
        ('returned', 'Returned'),
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    product_title = models.CharField(
        max_length=255
    )

    product_image = models.ImageField(
        upload_to='order_items/',
        blank=True,
        null=True
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending'
    )

    cancel_reason = models.TextField(
        blank=True
    )

    return_reason = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return (
            f"{self.order.order_id} - "
            f"{self.product_title}"
        )
    
    @property
    def subtotal(self):

        return (
            self.price
            * self.quantity
        )
    
class Wallet(models.Model):

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='wallet'
    )

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.email} Wallet"
    
class WalletTransaction(models.Model):

    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    description = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):      
        return (
            f"{self.wallet.user.email}"
            f" - {self.transaction_type}"
        )
    
class ReferralCode(models.Model):

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE
    )

    code = models.CharField(
        max_length=20,
        unique=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return self.code


class ReferralUsage(models.Model):

    referrer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='referrals_given'
    )

    referred_user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='referral_used'
    )

    referral_code = models.ForeignKey(
        ReferralCode,
        on_delete=models.CASCADE
    )

    reward_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"{self.referrer.email}"
            f" -> "
            f"{self.referred_user.email}"
        )
    
class Coupon(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    minimum_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    valid_from = models.DateTimeField()

    valid_to = models.DateTimeField()

    max_usage = models.PositiveIntegerField(
        default=1
    )

    used_count = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.code
    
class CouponUsage(models.Model):

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )

    used_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = (
            'coupon',
            'user'
        )

class ProductOffer(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='offers'
    )

    offer_percentage = models.PositiveIntegerField()

    valid_from = models.DateTimeField()

    valid_to = models.DateTimeField()

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"{self.product.title}"
            f" - {self.offer_percentage}%"
        )


class CategoryOffer(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='offers'
    )

    offer_percentage = models.PositiveIntegerField()

    valid_from = models.DateTimeField()

    valid_to = models.DateTimeField()

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"{self.category.name}"
            f" - {self.offer_percentage}%"
        )