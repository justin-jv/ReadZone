from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages

from .forms import (AdminLoginForm, CategoryForm, LanguageForm, ProductForm, CouponForm, ProductOfferForm, CategoryOfferForm)
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear, Coalesce

from accounts.models import CustomUser
from store.models import (Category, Language, Product, ProductImage, Order, OrderItem, Wallet, WalletTransaction, Coupon, ProductOffer, CategoryOffer, CouponUsage)

from django.utils import timezone
from datetime import timedelta

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount

from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer)

from reportlab.lib import colors

from reportlab.lib.styles import (getSampleStyleSheet)

from openpyxl import Workbook

from django.http import HttpResponse



import os




def admin_login(request):

    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.method == 'POST':

        form = AdminLoginForm(request.POST)

        if form.is_valid():

            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                email=email,
                password=password
            )

            if user is None:

                messages.error(
                    request,
                    'Invalid email or password.'
                )

            elif not user.is_superuser:

                messages.error(
                    request,
                    'Access denied.'
                )

            else:

                login(request, user)

                return redirect(
                    'admin_dashboard'
                )

    else:
        form = AdminLoginForm()

    return render(
        request,
        'admin_panel/admin_login.html',
        {'form': form}
    )


def admin_dashboard(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    total_users = (
        CustomUser.objects.filter(
            is_superuser=False
        ).count()
    )

    total_products = (
        Product.objects.count()
    )

    total_orders = (
        Order.objects.count()
    )

    total_revenue = (
        Order.objects.filter(
            payment_status='paid'
        ).aggregate(
            total=Sum(
                'total_amount'
            )
        )['total']
        or 0
    )

    top_products = (
        Product.objects.order_by(
            '-sales_count'
        )[:10]
    )

    period = request.GET.get(
        'period',
        'monthly'
    )


    if period == 'daily':

        sales_data = (

            Order.objects.filter(
                payment_status='paid'
            )

            .annotate(
                period=TruncDay(
                    'created_at'
                )
            )

            .values(
                'period'
            )

            .annotate(
                revenue=Sum(
                    'total_amount'
                )
            )

            .order_by(
                'period'
            )

        )

    elif period == 'weekly':

        sales_data = (

            Order.objects.filter(
                payment_status='paid'
            )

            .annotate(
                period=TruncWeek(
                    'created_at'
                )
            )

            .values(
                'period'
            )

            .annotate(
                revenue=Sum(
                    'total_amount'
                )
            )

            .order_by(
                'period'
            )

        )


    elif period == 'yearly':

        sales_data = (

            Order.objects.filter(
                payment_status='paid'
            )

            .annotate(
                period=TruncYear(
                    'created_at'
                )
            )

            .values(
                'period'
            )

            .annotate(
                revenue=Sum(
                    'total_amount'
                )
            )

            .order_by(
                'period'
            )

        )


    else:

        sales_data = (

            Order.objects.filter(
                payment_status='paid'
            )

            .annotate(
                period=TruncMonth(
                    'created_at'
                )
            )

            .values(
                'period'
            )

            .annotate(
                revenue=Sum(
                    'total_amount'
                )
            )

            .order_by(
                'period'
            )

        )


    
    top_categories = (

        Category.objects

        .annotate(

            total_sales=Coalesce(

                Sum(
                    'products__sales_count'
                ),

                0

            )

        )

        .filter(
            total_sales__gt=0
        )

        .order_by(
            '-total_sales'
        )[:10]

    )

    top_languages = (

        Language.objects

        .annotate(

            total_sales=Coalesce(

                Sum(
                    'products__sales_count'
                ),

                0

            )

        )

        .filter(
            total_sales__gt=0
        )

        .order_by(
            '-total_sales'
        )[:10]

    )


    context = {

        'total_users': total_users,

        'total_products': total_products,

        'total_orders': total_orders,

        'total_revenue': total_revenue,

        'top_products': top_products,

        'top_categories': top_categories,

        'top_languages': top_languages,

        'sales_labels': [

            (

                sale['period'].strftime('%d %b')

                if period == 'daily'
                
                else sale['period'].strftime('Week %W, %Y')
                if period == 'weekly'

                else sale['period'].strftime('%Y')
                if period == 'yearly'

                else sale['period'].strftime('%b %Y')

            )

            for sale in sales_data

        ],


        'sales_values': [

            float(
                sale['revenue']
            )

            for sale in sales_data

        ],


        'selected_period': period,

    }

    return render(
        request,
        'admin_panel/admin_dashboard.html',
        context
    )

def user_management(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    search_query = request.GET.get(
        'search',
        ''
    )

    users = CustomUser.objects.filter(
        is_superuser=False
    ).order_by('-created_at')

    if search_query:

        users = users.filter(
            Q(first_name__icontains=search_query)
            |
            Q(email__icontains=search_query)
            |
            Q(mobile_number__icontains=search_query)
        )

    paginator = Paginator(
        users,
        10
    )

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    return render(
        request,
        'admin_panel/user_management.html',
        context
    )

def block_user(request, user_id):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    user = CustomUser.objects.get(
        id=user_id,
        is_superuser=False
    )

    user.is_blocked = True
    user.save()

    return redirect('user_management')


def unblock_user(request, user_id):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    user = CustomUser.objects.get(
        id=user_id,
        is_superuser=False
    )

    user.is_blocked = False
    user.save()

    return redirect('user_management')

def delete_user(request, user_id):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    user = get_object_or_404(
        CustomUser,
        id=user_id,
        is_superuser=False
    )

    EmailAddress.objects.filter(
        user=user
    ).delete()

    SocialAccount.objects.filter(
        user=user
    ).delete()

    if user.profile_image:
        user.profile_image.delete(
            save=False
        )

    user.delete()

    messages.success(
        request,
        'User deleted successfully.'
    )

    return redirect(
        'user_management'
    )

def category_management(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    search_query = request.GET.get(
        'search',
        ''
    )

    status_filter = request.GET.get(
        'status',
        'all'
    )

    categories = Category.objects.all().order_by(
        '-created_at'
    )

    if search_query:

        categories = categories.filter(
            name__icontains=search_query
        )

    if status_filter == 'active':

        categories = categories.filter(
            is_active=True
        )

    elif status_filter == 'inactive':

        categories = categories.filter(
            is_active=False
        )

    paginator = Paginator(
        categories,
        10
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }

    return render(
        request,
        'admin_panel/category_list.html',
        context
    )


def add_category(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    if request.method == 'POST':

        form = CategoryForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Category added successfully.'
            )

            return redirect(
                'category_management'
            )

    else:

        form = CategoryForm()

    return render(
        request,
        'admin_panel/add_category.html',
        {
            'form': form
        }
    )


def edit_category(
    request,
    category_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    category = get_object_or_404(
        Category,
        id=category_id
    )

    if request.method == 'POST':

        form = CategoryForm(
            request.POST,
            instance=category
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Category updated successfully.'
            )

            return redirect(
                'category_management'
            )

    else:

        form = CategoryForm(
            instance=category
        )

    return render(
        request,
        'admin_panel/edit_category.html',
        {
            'form': form
        }
    )


def deactivate_category(
    request,
    category_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    category = get_object_or_404(
        Category,
        id=category_id
    )

    category.is_active = False

    category.save()

    messages.success(
        request,
        'Category deactivated.'
    )

    return redirect(
        'category_management'
    )


def activate_category(
    request,
    category_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    category = get_object_or_404(
        Category,
        id=category_id
    )

    category.is_active = True

    category.save()

    messages.success(
        request,
        'Category activated.'
    )

    return redirect(
        'category_management'
    )

def language_management(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    search_query = request.GET.get(
        'search',
        ''
    )

    status_filter = request.GET.get(
        'status',
        'all'
    )

    languages = Language.objects.all().order_by(
        '-created_at'
    )

    if search_query:

        languages = languages.filter(
            name__icontains=search_query
        )

    if status_filter == 'active':

        languages = languages.filter(
            is_active=True
        )

    elif status_filter == 'inactive':

        languages = languages.filter(
            is_active=False
        )

    paginator = Paginator(
        languages,
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
        'admin_panel/language_list.html',
        {
            'page_obj': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
        }
    )


def add_language(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    if request.method == 'POST':

        form = LanguageForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Language added successfully.'
            )

            return redirect(
                'language_management'
            )

    else:

        form = LanguageForm()

    return render(
        request,
        'admin_panel/add_language.html',
        {
            'form': form
        }
    )


def edit_language(
    request,
    language_id
):

    language = get_object_or_404(
        Language,
        id=language_id
    )

    if request.method == 'POST':

        form = LanguageForm(
            request.POST,
            instance=language
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Language updated successfully.'
            )

            return redirect(
                'language_management'
            )

    else:

        form = LanguageForm(
            instance=language
        )

    return render(
        request,
        'admin_panel/edit_language.html',
        {
            'form': form
        }
    )


def deactivate_language(
    request,
    language_id
):

    language = get_object_or_404(
        Language,
        id=language_id
    )

    language.is_active = False

    language.save()

    messages.success(
        request,
        'Language deactivated.'
    )

    return redirect(
        'language_management'
    )


def activate_language(
    request,
    language_id
):

    language = get_object_or_404(
        Language,
        id=language_id
    )

    language.is_active = True

    language.save()

    messages.success(
        request,
        'Language activated.'
    )

    return redirect(
        'language_management'
    )

def product_management(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    search_query = request.GET.get(
        'search',
        ''
    )

    category_filter = request.GET.get(
        'category',
        ''
    )

    language_filter = request.GET.get(
        'language',
        ''
    )

    status_filter = request.GET.get(
        'status',
        'all'
    )

    products = Product.objects.select_related(
        'category',
        'language'
    ).order_by(
        '-created_at'
    )

    if search_query:

        products = products.filter(
            Q(title__icontains=search_query)
            |
            Q(author__icontains=search_query)
            |
            Q(isbn__icontains=search_query)
            |
            Q(publisher__icontains=search_query)
        )

    if category_filter:

        products = products.filter(
            category_id=category_filter
        )

    if language_filter:

        products = products.filter(
            language_id=language_filter
        )

    if status_filter == 'active':

        products = products.filter(
            is_active=True
        )

    elif status_filter == 'inactive':

        products = products.filter(
            is_active=False
        )

    paginator = Paginator(
        products,
        10
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'language_filter': language_filter,
        'status_filter': status_filter,
        'categories': Category.objects.all(),
        'languages': Language.objects.all(),
    }

    return render(
        request,
        'admin_panel/product_list.html',
        context
    )


def add_product(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    if request.method == 'POST':

        form = ProductForm(
            request.POST,
            request.FILES
        )

        gallery_images = (
            request.FILES.getlist(
                'gallery_images'
            )
        )

        if len(gallery_images) < 3:

            messages.error(
                request,
                'Please upload at least 3 gallery images.'
            )

        elif len(gallery_images) > 5:

            messages.error(
                request,
                'Maximum 5 gallery images are allowed.'
            )

        elif form.is_valid():

            product = form.save()

            for image in gallery_images:

                ProductImage.objects.create(
                    product=product,
                    image=image
                )

            messages.success(
                request,
                'Product added successfully.'
            )

            return redirect(
                'product_management'
            )

    else:

        form = ProductForm()

    return render(
        request,
        'admin_panel/add_product.html',
        {
            'form': form
        }
    )

def edit_product(
    request,
    product_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if request.method == 'POST':

        old_image_path = None

        if product.cover_image:

            old_image_path = (
                product.cover_image.path
            )

        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product
        )

        gallery_images = (
            request.FILES.getlist(
                'gallery_images'
            )
        )

        if form.is_valid():

            updated_product = form.save()

            current_count = (
                updated_product.images.count()
            )

            if (
                current_count
                + len(gallery_images)
            ) > 5:

                messages.error(
                    request,
                    'Maximum 5 gallery images allowed.'
                )

                return redirect(
                    'edit_product',
                    product_id=product.id
                )

            for image in gallery_images:

                ProductImage.objects.create(
                    product=updated_product,
                    image=image
                )

            image_replaced = (
                'cover_image' in request.FILES
            )

            image_cleared = (
                'cover_image-clear'
                in request.POST
            )

            if (
                old_image_path
                and os.path.isfile(
                    old_image_path
                )
                and (
                    image_replaced
                    or image_cleared
                )
            ):

                os.remove(
                    old_image_path
                )

            messages.success(
                request,
                'Product updated successfully.'
            )

            return redirect(
                'product_management'
            )

    else:

        form = ProductForm(
            instance=product
        )

    return render(
        request,
        'admin_panel/edit_product.html',
        {
            'form': form,
            'product': product
        }
    )

def deactivate_product(
    request,
    product_id
):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    product.is_active = False

    product.save()

    messages.success(
        request,
        'Product deactivated.'
    )

    return redirect(
        'product_management'
    )


def activate_product(
    request,
    product_id
):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    product.is_active = True

    product.save()

    messages.success(
        request,
        'Product activated.'
    )

    return redirect(
        'product_management'
    )

def delete_product_image(
    request,
    image_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect('admin_login')

    product_image = get_object_or_404(
        ProductImage,
        id=image_id
    )

    product = product_image.product

    if product.images.count() <= 3:

        messages.error(
            request,
            'A product must have at least 3 gallery images.'
        )

        return redirect(
            'edit_product',
            product_id=product.id
        )

    if product_image.image:

        product_image.image.delete(
            save=False
        )

    product_image.delete()

    messages.success(
        request,
        'Gallery image deleted successfully.'
    )

    return redirect(
        'edit_product',
        product_id=product.id
    )

def update_order_status(order):

    statuses = list(

        order.items.values_list(
            'status',
            flat=True
        )

    )

    print(statuses)

    if not statuses:

        order.order_status = 'cancelled'

    elif all(
        status == 'cancelled'
        for status in statuses
    ):

        order.order_status = 'cancelled'

    elif any(
        status == 'cancelled'
        for status in statuses
    ):

        order.order_status = (
            'partially_cancelled'
        )

    elif all(
        status == 'returned'
        for status in statuses
    ):

        order.order_status = 'returned'

    elif any(
        status == 'return_requested'
        for status in statuses
    ):

        order.order_status = 'processing'

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

    else:

        order.order_status = 'pending'

    order.save()


def order_management(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    search = request.GET.get(
        'search',
        ''
    ).strip()

    status_filter = request.GET.get(
        'status',
        ''
    )

    orders = Order.objects.select_related(
        'user'
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
                full_name__icontains=search
            )

            |

            Q(
                user__email__icontains=search
            )

            |

            Q(
                items__product_title__icontains=search
            )

        ).distinct()

    if status_filter:

        orders = orders.filter(
            order_status=status_filter
        )

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
        'admin_panel/order_list.html',
        {
            'page_obj': page_obj,
            'search': search,
            'status_filter': status_filter,
        }
    )


def order_detail_admin(
    request,
    order_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    order = get_object_or_404(

        Order.objects.prefetch_related(
            'items'
        ),

        order_id=order_id

    )

    return render(
        request,
        'admin_panel/order_detail.html',
        {
            'order': order
        }
    )

def update_order_item_status(
    request,
    item_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    item = get_object_or_404(
        OrderItem,
        id=item_id
    )

    status = request.POST.get(
        'status'
    )

    # allowed_statuses = [

    #     'pending',
    #     'shipped',
    #     'out_for_delivery',
    #     'delivered'

    # ]

    # if status in allowed_statuses:

    #     item.status = status

    #     item.save()

    #     update_order_status(
    #         item.order
    #     )

    #     messages.success(
    #         request,
    #         'Status updated successfully.'
    #     )

    allowed_transitions = {

        'pending': ['shipped'],

        'shipped': ['out_for_delivery'],

        'out_for_delivery': ['delivered'],

    }

    if status in allowed_transitions.get(
        item.status,
        []
    ):

        item.status = status

        item.save()

        if (
            status == 'delivered'
            and item.order.payment_method == 'cod'
            and item.order.payment_status == 'pending'
        ):

            item.order.payment_status = 'paid'

            item.order.save(
                update_fields=['payment_status']
            )

        update_order_status(
            item.order
        )

        messages.success(
            request,
            'Status updated successfully.'
        )

    else:

        messages.error(
            request,
            'Invalid status transition.'
        )

    return redirect(
        'order_detail_admin',
        order_id=item.order.order_id
    )

def approve_return(
    request,
    item_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    item = get_object_or_404(
        OrderItem,
        id=item_id
    )

    if item.status != 'return_requested':

        messages.error(
            request,
            'Invalid return request.'
        )

        return redirect(
            'order_detail_admin',
            order_id=item.order.order_id
        )

    item.status = 'returned'

    item.save()

    if item.order.payment_status == 'paid':
        
        wallet, created = Wallet.objects.get_or_create(
            user=item.order.user
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
                f"Refund for returned item "
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
        'Return approved.'
    )

    return redirect(
        'order_detail_admin',
        order_id=item.order.order_id
    )

def coupon_management(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    coupons = Coupon.objects.order_by(
        '-created_at'
    )

    total_users = CustomUser.objects.filter(
        is_superuser=False
    ).count()

    for coupon in coupons:

        coupon.total_used = sum(

            usage.usage_count

            for usage in CouponUsage.objects.filter(
                coupon=coupon
            )

        )

        coupon.max_possible_usage = (

            total_users
            * coupon.max_usage_per_user

        )

    return render(
        request,
        'admin_panel/coupon_list.html',
        {
            'coupons': coupons,
            'total_users': total_users,
        }
    )

def add_coupon(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    if request.method == 'POST':

        form = CouponForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Coupon created successfully.'
            )

            return redirect(
                'coupon_management'
            )

    else:

        form = CouponForm()

    return render(
        request,
        'admin_panel/add_coupon.html',
        {
            'form': form
        }
    )

def delete_coupon(
    request,
    coupon_id
):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    coupon = get_object_or_404(
        Coupon,
        id=coupon_id
    )

    coupon.delete()

    messages.success(
        request,
        'Coupon deleted successfully.'
    )

    return redirect(
        'coupon_management'
    )

def product_offer_management(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    offers = ProductOffer.objects.select_related(
        'product'
    ).order_by(
        '-created_at'
    )

    context = {

        'offers': offers,

        'now': timezone.now()

    }

    return render(
        request,
        'admin_panel/product_offer_management.html',
        context
    )


def add_product_offer(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    if request.method == 'POST':

        form = ProductOfferForm(
            request.POST
        )

        if form.is_valid():

            product = form.cleaned_data[
                'product'
            ]

            existing_offer = ProductOffer.objects.filter(

                product=product,

                is_active=True

            )

            if existing_offer.exists():

                messages.error(

                    request,

                    'An active offer already exists for this product.'

                )

            else:

                form.save()

                messages.success(

                    request,

                    'Product offer added successfully.'

                )

                return redirect(
                    'product_offer_management'
                )

    else:

        form = ProductOfferForm()

    return render(
        request,
        'admin_panel/add_product_offer.html',
        {
            'form': form
        }
    )

def edit_product_offer(
    request,
    offer_id
):

    offer = get_object_or_404(

        ProductOffer,

        id=offer_id

    )

    if request.method == 'POST':

        form = ProductOfferForm(

            request.POST,

            instance=offer

        )

        if form.is_valid():

            form.save()

            messages.success(

                request,

                'Offer updated successfully.'

            )

            return redirect(
                'product_offer_management'
            )

    else:

        form = ProductOfferForm(
            instance=offer
        )

    return render(
        request,
        'admin_panel/add_product_offer.html',
        {
            'form': form
        }
    )

def toggle_product_offer(
    request,
    offer_id
):

    offer = get_object_or_404(

        ProductOffer,

        id=offer_id

    )

    if (

        offer.valid_to
        < timezone.now()

    ):

        messages.error(

            request,

            'Expired offers cannot be activated.'

        )

        return redirect(
            'product_offer_management'
        )

    offer.is_active = (
        not offer.is_active
    )

    offer.save()

    return redirect(
        'product_offer_management'
    )

def category_offer_management(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    offers = CategoryOffer.objects.select_related(
        'category'
    ).order_by(
        '-created_at'
    )

    context = {

        'offers': offers,

        'now': timezone.now()

    }

    return render(
        request,
        'admin_panel/category_offer_management.html',
        context
    )

def add_category_offer(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    if request.method == 'POST':

        form = CategoryOfferForm(
            request.POST
        )

        if form.is_valid():

            category = form.cleaned_data[
                'category'
            ]

            existing_offer = CategoryOffer.objects.filter(

                category=category,

                is_active=True

            )

            if existing_offer.exists():

                messages.error(

                    request,

                    'An active offer already exists for this category.'

                )

            else:

                form.save()

                messages.success(

                    request,

                    'Category offer added successfully.'

                )

                return redirect(
                    'category_offer_management'
                )

    else:

        form = CategoryOfferForm()

    return render(
        request,
        'admin_panel/add_category_offer.html',
        {
            'form': form
        }
    )

def edit_category_offer(
    request,
    offer_id
):

    offer = get_object_or_404(

        CategoryOffer,

        id=offer_id

    )

    if request.method == 'POST':

        form = CategoryOfferForm(

            request.POST,

            instance=offer

        )

        if form.is_valid():

            form.save()

            messages.success(

                request,

                'Offer updated successfully.'

            )

            return redirect(
                'category_offer_management'
            )

    else:

        form = CategoryOfferForm(
            instance=offer
        )

    return render(
        request,
        'admin_panel/add_category_offer.html',
        {
            'form': form
        }
    )

def toggle_category_offer(
    request,
    offer_id
):

    offer = get_object_or_404(

        CategoryOffer,

        id=offer_id

    )

    if (

        offer.valid_to
        < timezone.now()

    ):

        messages.error(

            request,

            'Expired offers cannot be activated.'

        )

        return redirect(
            'category_offer_management'
        )

    offer.is_active = (
        not offer.is_active
    )

    offer.save()

    return redirect(
        'category_offer_management'
    )

def sales_report(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    report_type = request.GET.get(
        'report_type',
        'daily'
    )

    today = timezone.now()

    orders = Order.objects.filter(
        payment_status='paid'
    )

    if report_type == 'daily':

        orders = orders.filter(
            created_at__date=today.date()
        )

    elif report_type == 'weekly':

        start_date = (
            today
            - timedelta(days=7)
        )

        orders = orders.filter(
            created_at__gte=start_date
        )

    elif report_type == 'monthly':

        orders = orders.filter(
            created_at__year=today.year,
            created_at__month=today.month
        )

    elif report_type == 'yearly':

        orders = orders.filter(
            created_at__year=today.year
        )

    elif report_type == 'custom':

        start_date = request.GET.get(
            'start_date'
        )

        end_date = request.GET.get(
            'end_date'
        )

        if start_date and end_date:

            orders = orders.filter(
                created_at__date__range=[
                    start_date,
                    end_date
                ]
            )

    total_orders = orders.count()

    gross_sales = 0

    offer_discount = 0

    coupon_discount = 0

    net_revenue = 0

    for order in orders:

        gross_sales += order.subtotal

        coupon_discount += (
            order.coupon_discount
        )

        net_revenue += (
            order.total_amount
        )

        for item in order.items.all():

            if item.product:

                regular_total = (

                    item.product.regular_price
                    * item.quantity

                )

                effective_total = (

                    item.price
                    * item.quantity

                )

                offer_discount += (

                    regular_total
                    - effective_total

                )

    context = {

        'orders': orders.order_by(
            '-created_at'
        ),

        'report_type': report_type,

        'total_orders': total_orders,

        'gross_sales': gross_sales,

        'coupon_discount': coupon_discount,

        'net_revenue': net_revenue,

        'offer_discount': offer_discount,

    }

    return render(

        request,

        'admin_panel/sales_report.html',

        context

    )

def sales_report_pdf(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    orders = Order.objects.filter(
        payment_status='paid'
    ).order_by(
        '-created_at'
    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ] = (
        'attachment; '
        'filename="sales_report.pdf"'
    )

    doc = SimpleDocTemplate(
        response
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            'ReadZone Sales Report',
            styles['Title']
        )
    )

    elements.append(
        Spacer(
            1,
            12
        )
    )

    data = [

        [

            'Order ID',

            'Customer',

            'Amount',

            'Coupon',

            'Payment'

        ]

    ]

    total_revenue = 0

    for order in orders:

        total_revenue += (
            order.total_amount
        )

        data.append([

            order.order_id,

            order.full_name,

            str(
                order.total_amount
            ),

            str(
                order.coupon_discount
            ),

            order.payment_method

        ])

    data.append([

        '',

        '',

        '',

        'Total Revenue',

        f'Rs.{total_revenue}'

    ])

    table = Table(data)

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

            )

        ])

    )

    elements.append(
        table
    )

    doc.build(
        elements
    )

    return response

def sales_report_excel(request):

    if not (
        request.user.is_authenticated
        and request.user.is_superuser
    ):
        return redirect(
            'admin_login'
        )

    orders = Order.objects.filter(
        payment_status='paid'
    ).order_by(
        '-created_at'
    )

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = (
        'Sales Report'
    )

    worksheet.append([

        'Order ID',

        'Customer',

        'Date',

        'Coupon Discount',

        'Total Amount',

        'Payment Method'

    ])

    for order in orders:

        worksheet.append([

            order.order_id,

            order.full_name,

            order.created_at.strftime(
                '%Y-%m-%d'
            ),

            float(
                order.coupon_discount
            ),

            float(
                order.total_amount
            ),

            order.payment_method

        ])

    response = HttpResponse(

        content_type=(
            'application/vnd.openxmlformats-'
            'officedocument.spreadsheetml.sheet'
        )

    )

    response[
        'Content-Disposition'
    ] = (
        'attachment; '
        'filename=sales_report.xlsx'
    )

    workbook.save(
        response
    )

    return response