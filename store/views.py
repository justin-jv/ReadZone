from django.core.paginator import Paginator

from django.db import transaction
from django.db.models import (Q, DecimalField, Count)
from django.db.models.functions import (Coalesce)

from django.shortcuts import (render, redirect, get_object_or_404)

from .models import (Product, Category, Language, Wishlist, Cart, CartItem, Address, Order, OrderItem, Wallet, WalletTransaction, Coupon, CouponUsage)
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse

from reportlab.platypus import (SimpleDocTemplate, Spacer, Paragraph, Table, TableStyle)

from reportlab.lib import colors

from reportlab.lib.styles import (getSampleStyleSheet)

from django.conf import settings

import razorpay
from decimal import Decimal
from django.http import JsonResponse


def generate_order_id():

    now = timezone.now()

    year = now.strftime('%y')
    month = now.strftime('%m')

    prefix = f'RZ{year}{month}'

    last_order = Order.objects.filter(
        order_id__startswith=prefix
    ).order_by(
        '-order_id'
    ).first()

    if last_order:

        last_number = int(
            last_order.order_id[-5:]
        )

        next_number = last_number + 1

    else:

        next_number = 1

    return (
        f'{prefix}'
        f'{str(next_number).zfill(5)}'
    )

def shop(request):

    products = Product.objects.filter(
        is_active=True,
        category__is_active=True,
        language__is_active=True
    ).annotate(
        db_effective_price=Coalesce(
            'sale_price',
            'regular_price',
            output_field=DecimalField()
        )
    )

    search = request.GET.get(
        'search',
        ''
    ).strip()

    category_id = request.GET.get(
        'category',
        ''
    )

    language_id = request.GET.get(
        'language',
        ''
    )

    min_price = request.GET.get(
        'min_price',
        ''
    )

    max_price = request.GET.get(
        'max_price',
        ''
    )

    sort = request.GET.get(
        'sort',
        ''
    )

    if search:

        products = products.filter(

            Q(title__icontains=search)

            |

            Q(author__icontains=search)

            |

            Q(publisher__icontains=search)

            |

            Q(isbn__icontains=search)

        )

    if category_id:

        products = products.filter(
            category_id=category_id
        )

    if language_id:

        products = products.filter(
            language_id=language_id
        )

    if min_price:

        try:

            products = products.filter(
                db_effective_price__gte=min_price
            )

        except ValueError:
            pass

    if max_price:

        try:

            products = products.filter(
                db_effective_price__lte=max_price
            )

        except ValueError:
            pass

    if sort == 'price_low':

        products = products.order_by(
            'db_effective_price'
        )

    elif sort == 'price_high':

        products = products.order_by(
            '-db_effective_price'
        )

    elif sort == 'a_z':

        products = products.order_by(
            'title'
        )

    elif sort == 'z_a':

        products = products.order_by(
            '-title'
        )

    elif sort == 'featured':

        products = products.order_by(
            '-is_featured',
            '-created_at'
        )

    elif sort == 'best_seller':

        products = products.order_by(
            '-sales_count'
        )

    else:

        products = products.order_by(
            '-created_at'
        )

    paginator = Paginator(
        products,
        12
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    wishlist_product_ids = []

    if request.user.is_authenticated:

        wishlist_product_ids = list(

            Wishlist.objects.filter(
                user=request.user
            ).values_list(
                'product_id',
                flat=True
            )

        )

    context = {

        'page_obj': page_obj,

        'categories': Category.objects.filter(
            is_active=True
        ),

        'languages': Language.objects.filter(
            is_active=True
        ),

        'search': search,

        'category_id': category_id,

        'language_id': language_id,

        'min_price': min_price,

        'max_price': max_price,

        'sort': sort,

        'wishlist_product_ids': wishlist_product_ids,

    }

    return render(
        request,
        'store/product_list.html',
        context
    )


def product_detail(
    request,
    slug
):

    product = get_object_or_404(
        Product.objects.select_related(
            'category',
            'language'
        ).prefetch_related(
            'images'
        ),
        slug=slug
    )

    if (
        not product.is_active
        or not product.category.is_active
        or not product.language.is_active
    ):

        return redirect(
            'shop'
        )

    related_products = Product.objects.filter(
        category=product.category,
        is_active=True,
        category__is_active=True,
        language__is_active=True
    ).exclude(
        id=product.id
    )[:8]

    is_wishlisted = False

    if request.user.is_authenticated:

        is_wishlisted = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()


    context = {

        'product': product,

        'related_products': related_products,

        'is_wishlisted': is_wishlisted,

    }

    return render(
        request,
        'store/product_detail.html',
        context
    )

@login_required
def wishlist(request):

    wishlist_items = Wishlist.objects.select_related(
        'product',
        'product__category',
        'product__language'
    ).filter(
        user=request.user,
        product__is_active=True,
        product__category__is_active=True,
        product__language__is_active=True
    ).order_by(
        '-created_at'
    )

    context = {

        'wishlist_items': wishlist_items

    }

    return render(
        request,
        'store/wishlist.html',
        context
    )


def toggle_wishlist(
    request,
    product_id
):

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True,
        category__is_active=True,
        language__is_active=True
    )

    if not request.user.is_authenticated:

        request.session[
            'wishlist_product_id'
        ] = product.id

        messages.info(
            request,
            'Please login to add books to your wishlist.'
        )

        return redirect(
            'login'
        )

    wishlist_item = Wishlist.objects.filter(
        user=request.user,
        product=product
    ).first()

    if wishlist_item:

        wishlist_item.delete()

        messages.success(
            request,
            'Book removed from wishlist.'
        )

    else:

        Wishlist.objects.create(
            user=request.user,
            product=product
        )

        messages.success(
            request,
            'Book added to wishlist.'
        )

    return redirect(
        request.META.get(
            'HTTP_REFERER',
            'shop'
        )
    )

@login_required
def add_to_cart(
    request,
    product_id
):

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    if product.stock <= 0:

        messages.error(
            request,
            'This book is currently out of stock.'
        )

        return redirect(
            'product_detail',
            slug=product.slug
        )

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    if cart.items.count() >= 20:

        messages.error(
            request,
            'Your cart already contains the maximum number of books allowed.'
        )

        return redirect(
            'product_detail',
            slug=product.slug
        )

    cart_item = CartItem.objects.filter(
        cart=cart,
        product=product
    ).first()

    if cart_item:

        if cart_item.quantity >= product.stock:

            messages.error(
                request,
                'Only limited stock is currently available for this book. Please try again later.'
            )

        else:

            cart_item.quantity += 1

            cart_item.save()

            Wishlist.objects.filter(
                user=request.user,
                product=product
            ).delete()

            messages.success(
                request,
                'Book added to cart successfully.'
            )

    else:

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1
        )

        Wishlist.objects.filter(
            user=request.user,
            product=product
        ).delete()

        messages.success(
            request,
            'Book added to cart successfully.'
        )
        
    return redirect(
        'product_detail',
        slug=product.slug
    )

@login_required
def cart(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    items = cart.items.select_related(
        'product'
    )

    total = sum(
        item.subtotal
        for item in items
    )

    context = {

        'cart': cart,

        'items': items,

        'total': total,

    }

    return render(
        request,
        'store/cart.html',
        context
    )


@login_required
def remove_from_cart(
    request,
    item_id
):

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    item.delete()

    messages.success(
        request,
        'Book removed from cart.'
    )

    return redirect(
        'cart'
    )


@login_required
def increase_quantity(
    request,
    item_id
):

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    if item.quantity < item.product.stock:

        item.quantity += 1

        item.save()

    else:

        messages.error(
            request,
            'Only limited stock is currently available for this book.'
        )

    return redirect(
        'cart'
    )


@login_required
def decrease_quantity(
    request,
    item_id
):

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    if item.quantity > 1:

        item.quantity -= 1

        item.save()

    else:

        messages.warning(
            request,
            'Minimum quantity is 1.'
        )

    return redirect(
        'cart'
    )

@login_required
def checkout(request):

    print(
        'SESSION COUPON:',
        request.session.get('coupon_id')
    )

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    items = cart.items.select_related(
        'product'
    )

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    if not items.exists():

        messages.warning(
            request,
            'Your cart is empty.'
        )

        return redirect(
            'cart'
        )

    for item in items:

        if (
            not item.product.is_active
            or item.quantity > item.product.stock
        ):

            messages.error(
                request,
                f'{item.product.title} is no longer available in the requested quantity.'
            )

            return redirect(
                'cart'
            )
        
    regular_total = 0

    sale_discount_total = 0 

    offer_discount = 0

    for item in items:

        item_regular_total = (
            item.product.regular_price
            * item.quantity
        )

        item_sale_total = (
            (
                item.product.sale_price
                or item.product.regular_price
            )
            * item.quantity
        )

        item_effective_total = (
            item.product.effective_price
            * item.quantity
        )

        regular_total += item_regular_total

        sale_discount_total += (
            item_regular_total
            - item_sale_total
        )

        offer_discount += (
            item_sale_total
            - item_effective_total
        )

    subtotal = sum(
        item.subtotal
        for item in items
    )

    shipping_charge = (
        0
        if subtotal >= 599
        else 40
    )

    tax_amount = 0

    grand_total = (
        subtotal
        + shipping_charge
        + tax_amount
    )

    coupon = None

    coupon_discount = 0

    coupon_id = request.session.get(
        'coupon_id'
    )

    if coupon_id:

        try:

            coupon = Coupon.objects.get(
                id=coupon_id
            )

            now = timezone.now()

            coupon_usage = CouponUsage.objects.filter(
                coupon=coupon,
                user=request.user
            ).first()

            if (

                coupon.is_active

                and coupon.valid_from <= now

                and coupon.valid_to >= now

                and (
                    not coupon_usage
                    or coupon_usage.usage_count
                    < coupon.max_usage_per_user
                )

                and subtotal >= coupon.minimum_purchase_amount

            ):

                coupon_discount = min(
                    coupon.discount_amount,
                    grand_total
                )

                grand_total -= (
                    coupon_discount
                )

            else:

                request.session.pop(
                    'coupon_id',
                    None
                )

                coupon = None

        except Coupon.DoesNotExist:

            request.session.pop(
                'coupon_id',
                None
            )

            coupon = None

    addresses = Address.objects.filter(
        user=request.user
    ).order_by(
        '-is_default',
        'created_at'
    )

    if not addresses.exists():

        messages.warning(
            request,
            'Please add an address before checkout.'
        )

        return redirect(
            '/add_address/?next=/checkout/'
        )

    checkout_address_id = (
        request.session.get(
            'checkout_address_id'
        )
    )

    if checkout_address_id:

        default_address = addresses.filter(
            id=checkout_address_id
        ).first()

        request.session.pop(
            'checkout_address_id',
            None
        )

    else:

        default_address = addresses.filter(
            is_default=True
        ).first()

        if not default_address:

            default_address = addresses.first()

    available_coupons = []

    for available_coupon in Coupon.objects.filter(

        is_active=True,

        valid_from__lte=timezone.now(),

        valid_to__gte=timezone.now()

    ).order_by(
        '-discount_amount'
    ):

        coupon_usage = CouponUsage.objects.filter(
            coupon=available_coupon,
            user=request.user
        ).first()

        if (

            coupon_usage
            and coupon_usage.usage_count
            >= available_coupon.max_usage_per_user

        ):

            continue

        available_coupons.append(
            available_coupon
        )

    context = {

        'items': items,

        'addresses': addresses,

        'default_address': default_address,

        'subtotal': subtotal,

        'shipping_charge': shipping_charge,

        'tax_amount': tax_amount,

        'grand_total': grand_total,

        'coupon': coupon,

        'coupon_discount': coupon_discount,

        'wallet': wallet,

        'available_coupons': available_coupons,

        'offer_discount': offer_discount,

        'regular_total': regular_total,

        'sale_discount_total': sale_discount_total,

        'razorpay_key_id': settings.RAZORPAY_KEY_ID,

    }

    return render(
        request,
        'store/checkout.html',
        context
    )


def update_order_status(order):

    statuses = list(

        order.items.values_list(
            'status',
            flat=True
        )

    )
    print("STATUSES =", statuses)

    if not statuses:

        order.order_status = 'cancelled'

    elif all(
        status == 'cancelled'
        for status in statuses
    ):

        order.order_status = 'cancelled'

    elif any(
        status == 'return_requested'
        for status in statuses
    ):

        order.order_status = 'processing'

    elif all(
        status == 'returned'
        for status in statuses
    ):
        print("RETURNED BLOCK HIT")
        order.order_status = 'returned'

    elif all(
        status == 'delivered'
        for status in statuses
    ):

        order.order_status = 'completed'
        

    elif any(
        status == 'out_for_delivery'
        for status in statuses
    ):

        order.order_status = 'processing'

    elif any(
        status == 'shipped'
        for status in statuses
    ):

        order.order_status = 'processing'

    elif any(
        status == 'cancelled'
        for status in statuses
    ):

        order.order_status = (
            'partially_cancelled'
        )

    else:

        order.order_status = 'pending'

    print("FINAL ORDER STATUS =", order.order_status)
    order.save(
        update_fields=[
            'order_status'
        ]
    )
    


@login_required
def place_order(request):

    if request.method != 'POST':

        return redirect(
            'checkout'
        )

    address_id = request.POST.get(
        'address_id'
    )

    payment_method = request.POST.get(
        'payment_method',
        'cod'
    )

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    items = cart.items.select_related(
        'product'
    )

    if not items.exists():

        messages.error(
            request,
            'Your cart is empty.'
        )

        return redirect(
            'cart'
        )

    subtotal = 0

    for item in items:

        if (
            not item.product.is_active
            or item.quantity > item.product.stock
        ):

            messages.error(
                request,
                f'{item.product.title} is no longer available in the requested quantity.'
            )

            return redirect(
                'cart'
            )

        subtotal += item.subtotal

    shipping_charge = (
        0
        if subtotal >= 599
        else 40
    )

    tax_amount = 0

    total_amount = (
        subtotal
        + shipping_charge
        + tax_amount
    )

    coupon = None

    coupon_discount = 0

    coupon_id = request.session.get(
        'coupon_id'
    )

    if coupon_id:

        try:

            coupon = Coupon.objects.get(
                id=coupon_id
            )

            now = timezone.now()

            coupon_usage = CouponUsage.objects.filter(
                coupon=coupon,
                user=request.user
            ).first()

            
            if not (

                coupon.is_active

                and coupon.valid_from <= now

                and coupon.valid_to >= now

                and (
                    not coupon_usage
                    or coupon_usage.usage_count
                    < coupon.max_usage_per_user
                )

                and subtotal >= coupon.minimum_purchase_amount

            ):

                request.session.pop(
                    'coupon_id',
                    None
                )

                messages.error(
                    request,
                    'Coupon is no longer valid.'
                )

                return redirect(
                    'checkout'
                )

            if (
                coupon_usage
                and coupon_usage.usage_count
                >= coupon.max_usage_per_user
            ):

                request.session.pop(
                    'coupon_id',
                    None
                )

                messages.error(
                    request,
                    'You have reached the maximum usage limit for this coupon.'
                )

                return redirect(
                    'checkout'
                )

            coupon_discount = min(
                coupon.discount_amount,
                total_amount
            )

            total_amount -= (
                coupon_discount
            )

        except Coupon.DoesNotExist:

            request.session.pop(
                'coupon_id',
                None
            )

    if payment_method == 'wallet':

        wallet, created = Wallet.objects.get_or_create(
            user=request.user
        )

        if wallet.balance < total_amount:

            messages.error(
                request,
                'Insufficient wallet balance.'
            )

            return redirect(
                'checkout'
            )

    with transaction.atomic():

        order = Order.objects.create(

            order_id=generate_order_id(),

            user=request.user,

            full_name=address.full_name,

            mobile_number=address.mobile_number,

            house_name=address.house_name,

            area_street=address.area_street,

            landmark=address.landmark,

            city=address.city,

            district=address.district,

            state=address.state,

            country=address.country,

            pincode=address.pincode,

            subtotal=subtotal,

            shipping_charge=shipping_charge,

            tax_amount=tax_amount,

            total_amount=total_amount,

            coupon=coupon,

            coupon_discount=coupon_discount,

            payment_method=payment_method,

            payment_status=(
                'paid'
                if payment_method == 'wallet'
                else 'pending'
            ),

            order_status='pending'
        )

        for item in items:

            OrderItem.objects.create(

                order=order,

                product=item.product,

                product_title=item.product.title,

                product_image = item.product.cover_image,

                quantity=item.quantity,

                price=item.product.effective_price,

                status='pending'
            )

            item.product.stock -= (
                item.quantity
            )

            item.product.sales_count += (
                item.quantity
            )

            item.product.save()

        if payment_method == 'wallet':

            wallet.balance -= total_amount

            wallet.save()

            WalletTransaction.objects.create(

                wallet=wallet,

                transaction_type='debit',

                amount=total_amount,

                description=(
                    f"Wallet payment for "
                    f"order {order.order_id}"
                )
            )

        if coupon:
            
            coupon_usage, created = (
                CouponUsage.objects.get_or_create(
                    coupon=coupon,
                    user=request.user
                )
            )

            coupon_usage.usage_count += 1

            coupon_usage.save(
                update_fields=[
                    'usage_count'
                ]
            )

        items.delete()

    request.session.pop(
        'coupon_id',
        None
    )

    messages.success(
        request,
        'Order placed successfully.'
    )

    return redirect(
        'order_success',
        order_id=order.order_id
    )

@login_required
def order_success(
    request,
    order_id
):

    return render(
        request,
        'store/order_success.html',
        {
            'order_id': order_id
        }
    )

@login_required
def my_orders(request):

    search = request.GET.get(
        'search',
        ''
    ).strip()

    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related(
        'items'
    ).order_by(
        '-created_at'
    )

    if search:

        orders = orders.filter(

            Q(
                order_id__icontains=search
            )

            |

            Q(
                items__product_title__icontains=search
            )

        ).distinct()

    paginator = Paginator(
        orders,
        10
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        'store/my_orders.html',
        {
            'page_obj': page_obj,
            'search': search
        }
    )

@login_required
def order_detail(
    request,
    order_id
):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items'
        ),
        order_id=order_id,
        user=request.user
    )

    return render(
        request,
        'store/order_detail.html',
        {
            'order': order
        }
    )

@login_required
def cancel_order_item(
    request,
    item_id
):

    item = get_object_or_404(

        OrderItem,

        id=item_id,

        order__user=request.user

    )

    if item.status not in [

        'pending',

        'shipped'

    ]:

        messages.error(

            request,

            'This item cannot be cancelled.'

        )

        return redirect(

            'order_detail',

            order_id=item.order.order_id

        )

    reason = request.POST.get(
        'cancel_reason',
        ''
    ).strip()

    item.status = 'cancelled'

    item.cancel_reason = reason

    item.save()

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    refund_amount = (
        item.price
        * item.quantity
    )

    wallet.balance += refund_amount

    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type='credit',
        amount=refund_amount,
        description=(
            f"Refund for cancelled item "
            f"{item.product_title}"
        )
    )

    if item.product:

        item.product.stock += (
            item.quantity
        )

        item.product.save()

    update_order_status(
        item.order
    )

    messages.success(

        request,

        'Item cancelled successfully.'

    )

    return redirect(

        'order_detail',

        order_id=item.order.order_id

    )

@login_required
def return_order_item(
    request,
    item_id
):

    item = get_object_or_404(

        OrderItem,

        id=item_id,

        order__user=request.user

    )

    if item.status != 'delivered':

        messages.error(

            request,

            'Only delivered items can be returned.'

        )

        return redirect(

            'order_detail',

            order_id=item.order.order_id

        )

    reason = request.POST.get(
        'return_reason',
        ''
    ).strip()

    if not reason:

        messages.error(

            request,

            'Return reason is required.'

        )

        return redirect(

            'order_detail',

            order_id=item.order.order_id

        )

    item.status = (
        'return_requested'
    )

    item.return_reason = reason

    item.save()

    update_order_status(
        item.order
    )

    messages.success(

        request,

        'Return request submitted successfully.'

    )

    return redirect(

        'order_detail',

        order_id=item.order.order_id

    )

@login_required
def download_invoice(
    request,
    order_id
):

    order = get_object_or_404(

        Order.objects.prefetch_related(
            'items'
        ),

        order_id=order_id,

        user=request.user

    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ] = (
        f'attachment; '
        f'filename="ReadZone_Invoice_{order.order_id}.pdf"'
    )

    doc = SimpleDocTemplate(
        response
    )

    styles = (
        getSampleStyleSheet()
    )

    elements = []

    elements.append(

        Paragraph(
            "READZONE",
            styles['Title']
        )

    )

    elements.append(

        Paragraph(
            "TAX INVOICE",
            styles['Heading2']
        )

    )

    elements.append(
        Spacer(1, 12)
    )

    elements.append(

        Paragraph(
            f"<b>Invoice No:</b> INV-{order.order_id}",
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            f"<b>Order ID:</b> {order.order_id}",
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            # f"<b>Date:</b> {order.created_at.strftime('%d-%m-%Y')}",
            f"<b>Date:</b> {timezone.localtime(order.created_at).strftime('%d-%m-%Y')}", # Local Time
            styles['Normal']
        )

    )

    elements.append(
        Spacer(1, 12)
    )

    elements.append(

        Paragraph(
            "<b>Billing Address</b>",
            styles['Heading3']
        )

    )

    elements.append(

        Paragraph(
            order.full_name,
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            order.house_name,
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            order.area_street,
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            (
                f"{order.city}, "
                f"{order.district}, "
                f"{order.state} - "
                f"{order.pincode}"
            ),
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            f"Mobile: {order.mobile_number}",
            styles['Normal']
        )

    )

    elements.append(
        Spacer(1, 15)
    )

    table_data = [

        [
            'Book',
            'Qty',
            'Price',
            'Total'
        ]

    ]

    for item in order.items.all():

        table_data.append(

            [

                item.product_title,

                str(
                    item.quantity
                ),

                f"Rs. {item.price}",

                f"Rs. {item.subtotal}"

            ]

        )

    table = Table(
        table_data,
        colWidths=[
            250,
            60,
            80,
            80
        ]
    )

    table.setStyle(

        TableStyle([

            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),

            (
                'GRID',
                (0, 0),
                (-1, -1),
                1,
                colors.black
            ),

            (
                'FONTNAME',
                (0, 0),
                (-1, 0),
                'Helvetica-Bold'
            ),

        ])

    )

    elements.append(
        table
    )

    elements.append(
        Spacer(1, 20)
    )

    elements.append(

        Paragraph(
            (
                f"<b>Subtotal:</b> "
                f"Rs. {order.subtotal}"
            ),
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            (
                f"<b>Shipping:</b> "
                f"Rs. {order.shipping_charge}"
            ),
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            (
                f"<b>Tax:</b> "
                f"Rs. {order.tax_amount}"
            ),
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            (
                f"<b>Grand Total:</b> "
                f"Rs. {order.total_amount}"
            ),
            styles['Heading3']
        )

    )

    elements.append(
        Spacer(1, 20)
    )

    elements.append(

        Paragraph(
            (
                f"<b>Payment Method:</b> "
                f"{order.get_payment_method_display()}"
            ),
            styles['Normal']
        )

    )

    elements.append(

        Paragraph(
            (
                f"<b>Payment Status:</b> "
                f"{order.get_payment_status_display()}"
            ),
            styles['Normal']
        )

    )

    elements.append(
        Spacer(1, 20)
    )

    elements.append(

        Paragraph(
            (
                "Thank you for shopping "
                "with ReadZone."
            ),
            styles['Normal']
        )

    )

    doc.build(
        elements
    )

    return response

@login_required
def wallet(request):

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    transactions = wallet.transactions.order_by(
        '-created_at'
    )

    context = {

        'wallet': wallet,

        'transactions': transactions,

    }

    return render(
        request,
        'store/wallet.html',
        context
    )

# @login_required
# def apply_coupon(request):

#     if request.method != 'POST':

#         return redirect(
#             'checkout'
#         )

#     if request.session.get(
#         'coupon_id'
#     ):

#         messages.error(
#             request,
#             'Remove current coupon first.'
#         )

#         return redirect(
#             'checkout'
#         )

#     code = request.POST.get(
#         'coupon_code',
#         ''
#     ).strip().upper()

#     try:

#         coupon = Coupon.objects.get(
#             code=code
#         )

#     except Coupon.DoesNotExist:

#         messages.error(
#             request,
#             'Invalid coupon.'
#         )

#         return redirect(
#             'checkout'
#         )

#     cart = Cart.objects.get(
#         user=request.user
#     )

#     subtotal = sum(
#         item.subtotal
#         for item in cart.items.all()
#     )

#     now = timezone.now()

#     if not coupon.is_active:

#         messages.error(
#             request,
#             'Coupon is inactive.'
#         )

#     elif coupon.valid_from > now:

#         messages.error(
#             request,
#             'Coupon is not active yet.'
#         )

#     elif coupon.valid_to < now:

#         messages.error(
#             request,
#             'Coupon expired.'
#         )

#     elif coupon.used_count >= coupon.max_usage:

#         messages.error(
#             request,
#             'Coupon usage limit reached.'
#         )

#     elif subtotal < coupon.minimum_purchase_amount:

#         messages.error(
#             request,
#             (
#                 f'Minimum purchase amount '
#                 f'₹{coupon.minimum_purchase_amount}'
#             )
#         )

#     elif CouponUsage.objects.filter(
#         coupon=coupon,
#         user=request.user
#     ).exists():

#         messages.error(
#             request,
#             'You already used this coupon.'
#         )

#     else:

#         request.session[
#             'coupon_id'
#         ] = coupon.id

#         messages.success(
#             request,
#             'Coupon applied successfully.'
#         )

#     return redirect(
#         'checkout'
#     )

# @login_required
# def remove_coupon(request):

#     request.session.pop(
#         'coupon_id',
#         None
#     )

#     messages.success(
#         request,
#         'Coupon removed.'
#     )

#     return redirect(
#         'checkout'
#     )

@login_required
def apply_coupon(
    request,
    coupon_id
):

    coupon = get_object_or_404(
        Coupon,
        id=coupon_id
    )

    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    subtotal = sum(
        item.subtotal
        for item in cart.items.all()
    )

    now = timezone.now()

    if not coupon.is_active:

        messages.error(
            request,
            'Coupon is inactive.'
        )

        return redirect(
            'checkout'
        )

    if now < coupon.valid_from:

        messages.error(
            request,
            'Coupon not started yet.'
        )

        return redirect(
            'checkout'
        )

    if now > coupon.valid_to:

        messages.error(
            request,
            'Coupon expired.'
        )

        return redirect(
            'checkout'
        )

    if subtotal < coupon.minimum_purchase_amount:

        messages.error(
            request,
            (
                f'Minimum purchase ₹'
                f'{coupon.minimum_purchase_amount}'
                f' required.'
            )
        )

        return redirect(
            'checkout'
        )
    
    coupon_usage = CouponUsage.objects.filter(
        coupon=coupon,
        user=request.user
    ).first()

    if (
        coupon_usage
        and coupon_usage.usage_count
        >= coupon.max_usage_per_user
    ):

        messages.error(
            request,
            'You have reached the maximum usage limit for this coupon.'
        )

        return redirect(
            'checkout'
        )    
    
    print('APPLYING COUPON:', coupon.code)
    print('SUBTOTAL:', subtotal)
    print('MIN PURCHASE:', coupon.minimum_purchase_amount)

    request.session[
        'coupon_id'
    ] = coupon.id

    messages.success(
        request,
        'Coupon applied successfully.'
    )

    return redirect(
        'checkout'
    )

@login_required
def remove_coupon(request):

    request.session.pop(
        'coupon_id',
        None
    )

    messages.success(
        request,
        'Coupon removed.'
    )

    return redirect(
        'checkout'
    )

@login_required
def create_razorpay_order(request):

    if request.method != 'POST':

        return JsonResponse(
            {
                'success': False
            }
        )

    address_id = request.POST.get(
        'address_id'
    )

    request.session[
        'checkout_address_id'
    ] = address_id

    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    subtotal = sum(
        item.subtotal
        for item in cart.items.all()
    )

    shipping_charge = (
        0
        if subtotal >= 599
        else 40
    )

    total_amount = (
        subtotal
        + shipping_charge
    )

    coupon_id = request.session.get(
        'coupon_id'
    )

    if coupon_id:

        try:

            coupon = Coupon.objects.get(
                id=coupon_id
            )

            coupon_discount = min(
                coupon.discount_amount,
                total_amount
            )

            total_amount -= (
                coupon_discount
            )

        except Coupon.DoesNotExist:

            pass

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    razorpay_order = client.order.create({

        'amount': int(
            Decimal(total_amount)
            * 100
        ),

        'currency': 'INR',


    })

    request.session[
        'razorpay_order_id'
    ] = razorpay_order['id']

    return JsonResponse({

        'success': True,

        'order_id': razorpay_order['id'],

        'amount': razorpay_order['amount'],

        'key': settings.RAZORPAY_KEY_ID

    })

@login_required
def verify_razorpay_payment(request):

    razorpay_payment_id = request.GET.get(
        'razorpay_payment_id'
    )

    razorpay_order_id = request.GET.get(
        'razorpay_order_id'
    )

    razorpay_signature = request.GET.get(
        'razorpay_signature'
    )

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    try:

        client.utility.verify_payment_signature({

            'razorpay_order_id':
            razorpay_order_id,

            'razorpay_payment_id':
            razorpay_payment_id,

            'razorpay_signature':
            razorpay_signature,

        })

    except:

        messages.error(
            request,
            'Payment verification failed.'
        )

        return redirect(
            'checkout'
        )

    address_id = request.session.get(
        'checkout_address_id'
    )

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    items = cart.items.select_related(
        'product'
    )

    subtotal = sum(
        item.subtotal
        for item in items
    )

    shipping_charge = (
        0
        if subtotal >= 599
        else 40
    )

    tax_amount = 0

    total_amount = (
        subtotal
        + shipping_charge
        + tax_amount
    )

    coupon = None

    coupon_discount = 0

    coupon_id = request.session.get(
        'coupon_id'
    )

    if coupon_id:

        try:

            coupon = Coupon.objects.get(
                id=coupon_id
            )

            coupon_discount = min(
                coupon.discount_amount,
                total_amount
            )

            total_amount -= (
                coupon_discount
            )

        except Coupon.DoesNotExist:

            coupon = None

    with transaction.atomic():

        order = Order.objects.create(

            order_id=generate_order_id(),

            user=request.user,

            full_name=address.full_name,

            mobile_number=address.mobile_number,

            house_name=address.house_name,

            area_street=address.area_street,

            landmark=address.landmark,

            city=address.city,

            district=address.district,

            state=address.state,

            country=address.country,

            pincode=address.pincode,

            subtotal=subtotal,

            shipping_charge=shipping_charge,

            tax_amount=tax_amount,

            total_amount=total_amount,

            coupon=coupon,

            coupon_discount=coupon_discount,

            payment_method='online',

            payment_status='paid',

            razorpay_order_id=razorpay_order_id,

            razorpay_payment_id=razorpay_payment_id,

            razorpay_signature=razorpay_signature,

            order_status='pending'
        )

        for item in items:

            OrderItem.objects.create(

                order=order,

                product=item.product,

                product_title=item.product.title,

                product_image=item.product.cover_image,

                quantity=item.quantity,

                price=item.product.effective_price,

                status='pending'
            )

            item.product.stock -= (
                item.quantity
            )

            item.product.sales_count += (
                item.quantity
            )

            item.product.save()

        if coupon:

            coupon_usage, created = (
                CouponUsage.objects.get_or_create(
                    coupon=coupon,
                    user=request.user
                )
            )

            coupon_usage.usage_count += 1

            coupon_usage.save(
                update_fields=[
                    'usage_count'
                ]
            )

        items.delete()

    request.session.pop(
        'coupon_id',
        None
    )

    request.session.pop(
        'checkout_address_id',
        None
    )

    request.session.pop(
        'razorpay_order_id',
        None
    )

    messages.success(
        request,
        'Payment successful.'
    )

    return redirect(
        'order_success',
        order_id=order.order_id
    )