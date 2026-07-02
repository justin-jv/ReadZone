from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignupForm, OTPVerificationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, EditProfileForm, ChangePasswordForm, ChangeEmailForm
from .models import OTPVerification, CustomUser
from .utils import generate_otp, send_otp_email
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from store.forms import AddressForm
from store.models import (Address, Product, Wishlist)
from django.conf import settings
from django.core.mail import send_mail

# Create your views here.

def landing_page(request):

    new_arrivals = Product.objects.filter(
        is_active=True,
        category__is_active=True,
        language__is_active=True
    ).order_by(
        '-created_at'
    )[:4]

    best_sellers = Product.objects.filter(
        is_active=True,
        category__is_active=True,
        language__is_active=True
    ).order_by(
        '-sales_count'
    )[:4]

    top_book = Product.objects.filter(
        is_active=True
    ).order_by(
        '-sales_count',
        '-created_at'
    ).first()

    context = {

        'new_arrivals': new_arrivals,

        'best_sellers': best_sellers,

        'top_book': top_book,

    }

    return render(
        request,
        'accounts/landing_page.html',
        context
    )

def signup(request):

    if request.method == "POST":

        form = SignupForm(request.POST)

        if form.is_valid():

            otp = generate_otp()

            email = form.cleaned_data['email']

            OTPVerification.objects.filter(
                email=email,
                purpose='signup'
            ).delete()

            OTPVerification.objects.create(
                email=email,
                otp=otp,
                purpose='signup'
            )

            request.session['signup_data'] = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'email': email,
                'mobile_number': form.cleaned_data['mobile_number'],
                'password': form.cleaned_data['password'],
            }

            send_otp_email(email, otp)

            return redirect('verify_otp')

    else:
        form = SignupForm()

    return render(
        request,
        'accounts/signup.html',
        {'form': form}
    )

def verify_otp(request):

    signup_data = request.session.get('signup_data')

    if not signup_data:
        return redirect('signup')

    email = signup_data['email']

    otp_record = OTPVerification.objects.filter(
        email=email,
        purpose='signup'
    ).first()

    if not otp_record:
        messages.error(request, "OTP not found.")
        return redirect('signup')

    remaining_attempts = 3 - otp_record.attempt_count

    if request.method == 'POST':

        form = OTPVerificationForm(request.POST)

        if form.is_valid():

            entered_otp = form.cleaned_data['otp']

            if timezone.now() > otp_record.created_at + timedelta(seconds=60):

                messages.error(
                    request,
                    "OTP has expired. Please resend OTP."
                )

                return redirect('verify_otp')

            if otp_record.attempt_count >= 3:

                messages.error(
                    request,
                    "Maximum attempts reached. Please resend OTP."
                )

                return redirect('verify_otp')

            if entered_otp != otp_record.otp:

                otp_record.attempt_count += 1
                otp_record.save()

                messages.error(
                    request,
                    f"Invalid OTP. Attempts remaining: {2 - otp_record.attempt_count + 1}"
                )

                return redirect('verify_otp')

            CustomUser.objects.create_user(
                email=signup_data['email'],
                password=signup_data['password'],
                first_name=signup_data['first_name'],
                last_name=signup_data['last_name'],
                mobile_number=signup_data['mobile_number'],
                is_verified=True
            )

            otp_record.delete()

            del request.session['signup_data']

            messages.success(
                request,
                "Account created successfully. Please login."
            )

            return redirect('login')

    else:
        form = OTPVerificationForm()

    context = {
        'form': form,
        'remaining_attempts': remaining_attempts,
        'otp_created_at': otp_record.created_at.timestamp(),
        'attempt_limit_reached': otp_record.attempt_count >= 3,
    }

    return render(
        request,
        'accounts/verify_otp.html',
        context
    )

def resend_otp(request):

    signup_data = request.session.get('signup_data')

    if not signup_data:
        return redirect('signup')

    email = signup_data['email']

    OTPVerification.objects.filter(
        email=email,
        purpose='signup'
    ).delete()

    otp = generate_otp()

    OTPVerification.objects.create(
        email=email,
        otp=otp,
        purpose='signup'
    )

    send_otp_email(email, otp)

    messages.success(
        request,
        "A new OTP has been sent to your email."
    )

    return redirect('verify_otp')

def login_view(request):

    if request.user.is_authenticated:
        return redirect('landing_page')

    if request.method == 'POST':

        form = LoginForm(request.POST)

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
                    "Invalid email or password."
                )

            elif user.is_blocked:

                messages.error(
                    request,
                    "Your account has been blocked."
                )

            elif not user.is_verified:

                messages.error(
                    request,
                    "Please verify your account."
                )

            else:

                login(
                    request,
                    user
                )

                wishlist_product_id = (
                    request.session.get(
                        'wishlist_product_id'
                    )
                )

                if wishlist_product_id:

                    try:

                        product = Product.objects.get(
                            id=wishlist_product_id,
                            is_active=True,
                            category__is_active=True,
                            language__is_active=True
                        )

                        Wishlist.objects.get_or_create(
                            user=user,
                            product=product
                        )

                        messages.success(
                            request,
                            'Book added to wishlist successfully.'
                        )

                    except Product.DoesNotExist:

                        pass

                    del request.session[
                        'wishlist_product_id'
                    ]

                next_url = request.GET.get(
                    'next'
                )

                if next_url:

                    return redirect(
                        next_url
                    )

                return redirect(
                    'landing_page'
                )

    else:

        form = LoginForm()

    return render(
        request,
        'accounts/login.html',
        {
            'form': form
        }
    )

def logout_view(request):

    is_admin = request.user.is_superuser

    logout(request)

    if is_admin:

        return redirect('admin_login')

    return redirect('landing_page')


def forgot_password(request):

    if request.method == 'POST':

        form = ForgotPasswordForm(request.POST)

        if form.is_valid():

            email = form.cleaned_data['email']

            otp = generate_otp()

            OTPVerification.objects.filter(
                email=email,
                purpose='forgot_password'
            ).delete()

            OTPVerification.objects.create(
                email=email,
                otp=otp,
                purpose='forgot_password'
            )

            request.session['forgot_password_email'] = email

            send_otp_email(email, otp)

            return redirect(
                'forgot_password_verify_otp'
            )

    else:
        form = ForgotPasswordForm()

    return render(
        request,
        'accounts/forgot_password.html',
        {'form': form}
    )

def forgot_password_verify_otp(request):

    email = request.session.get(
        'forgot_password_email'
    )

    if not email:
        return redirect('forgot_password')

    otp_record = OTPVerification.objects.filter(
        email=email,
        purpose='forgot_password'
    ).first()

    if not otp_record:

        messages.error(
            request,
            "OTP not found."
        )

        return redirect('forgot_password')

    remaining_attempts = (
        3 - otp_record.attempt_count
    )

    if request.method == 'POST':

        form = OTPVerificationForm(
            request.POST
        )

        if form.is_valid():

            entered_otp = (
                form.cleaned_data['otp']
            )

            if timezone.now() > (
                otp_record.created_at
                + timedelta(seconds=60)
            ):

                messages.error(
                    request,
                    "OTP has expired. Please resend OTP."
                )

                return redirect(
                    'forgot_password_verify_otp'
                )

            if otp_record.attempt_count >= 3:

                messages.error(
                    request,
                    "Maximum attempts reached. Please resend OTP."
                )

                return redirect(
                    'forgot_password_verify_otp'
                )

            if entered_otp != otp_record.otp:

                otp_record.attempt_count += 1
                otp_record.save()

                messages.error(
                    request,
                    f"Invalid OTP. Attempts remaining: {3 - otp_record.attempt_count}"
                )

                return redirect(
                    'forgot_password_verify_otp'
                )

            request.session[
                'password_reset_verified'
            ] = True

            return redirect(
                'reset_password'
            )

    else:
        form = OTPVerificationForm()

    context = {
        'form': form,
        'remaining_attempts': remaining_attempts,
        'otp_created_at':
            otp_record.created_at.timestamp(),
        'attempt_limit_reached':
            otp_record.attempt_count >= 3,
    }

    return render(
        request,
        'accounts/forgot_password_verify_otp.html',
        context
    )

def forgot_password_resend_otp(request):

    email = request.session.get(
        'forgot_password_email'
    )

    if not email:
        return redirect('forgot_password')

    OTPVerification.objects.filter(
        email=email,
        purpose='forgot_password'
    ).delete()

    otp = generate_otp()

    OTPVerification.objects.create(
        email=email,
        otp=otp,
        purpose='forgot_password'
    )

    send_otp_email(email, otp)

    messages.success(
        request,
        "A new OTP has been sent to your email."
    )

    return redirect(
        'forgot_password_verify_otp'
    )

def reset_password(request):

    email = request.session.get(
        'forgot_password_email'
    )

    verified = request.session.get(
        'password_reset_verified'
    )

    if not email or not verified:
        return redirect('forgot_password')

    if request.method == 'POST':

        form = ResetPasswordForm(
            request.POST
        )

        if form.is_valid():

            user = CustomUser.objects.get(
                email=email
            )

            user.set_password(
                form.cleaned_data['password']
            )

            user.save()

            OTPVerification.objects.filter(
                email=email,
                purpose='forgot_password'
            ).delete()

            del request.session[
                'forgot_password_email'
            ]

            del request.session[
                'password_reset_verified'
            ]

            messages.success(
                request,
                "Password changed successfully. Please login."
            )

            return redirect('login')

    else:
        form = ResetPasswordForm()

    return render(
        request,
        'accounts/reset_password.html',
        {'form': form}
    )

@login_required
def profile_view(request):

    return render(
        request,
        'accounts/profile.html',
        {
            'user_obj': request.user
        }
    )

@login_required
def edit_profile(request):

    if request.method == 'POST':

        form = EditProfileForm(
            request.POST,
            request.FILES,
            instance=request.user,
            user=request.user
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Profile updated successfully.'
            )

            return redirect('profile')

    else:

        form = EditProfileForm(
            instance=request.user,
            user=request.user
        )

    return render(
        request,
        'accounts/edit_profile.html',
        {
            'form': form,
            'user_obj': request.user
        }
    )

@login_required
def change_password(request):

    if request.method == 'POST':

        form = ChangePasswordForm(
            request.POST
        )

        if form.is_valid():

            current_password = form.cleaned_data[
                'current_password'
            ]

            new_password = form.cleaned_data[
                'new_password'
            ]

            if not request.user.check_password(
                current_password
            ):

                messages.error(
                    request,
                    'Current password is incorrect.'
                )

            elif current_password == new_password:

                messages.error(
                    request,
                    'New password cannot be the same as current password.'
                )

            else:

                request.user.set_password(
                    new_password
                )

                request.user.save()

                messages.success(
                    request,
                    'Password changed successfully. Please login again.'
                )

                logout(request)

                return redirect(
                    'login'
                )

    else:

        form = ChangePasswordForm()

    return render(
        request,
        'accounts/change_password.html',
        {
            'form': form
        }
    )

@login_required
def addresses(request):

    address_list = Address.objects.filter(
        user=request.user
    ).order_by(
        '-is_default',
        'created_at'
    )

    return render(
        request,
        'accounts/addresses.html',
        {
            'address_list': address_list
        }
    )

@login_required
def add_address(request):

    if request.method == 'POST':

        form = AddressForm(
            request.POST
        )

        if form.is_valid():

            address = form.save(
                commit=False
            )

            address.user = request.user

            if not Address.objects.filter(
                user=request.user
            ).exists():

                address.is_default = True

            address.save()

            next_url = request.GET.get(
                'next'
            )
            if next_url == '/checkout/':
                request.session[
                    'checkout_address_id'
                ] = address.id


            messages.success(
                request,
                'Address added successfully.'
            )

            next_url = request.GET.get('next')

            if next_url:
                return redirect(
                    next_url
                )

            return redirect(
                'addresses'
            )

    else:

        form = AddressForm()

    return render(
        request,
        'accounts/add_address.html',
        {
            'form': form
        }
    )

@login_required
def edit_address(
    request,
    address_id
):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    if request.method == 'POST':

        form = AddressForm(
            request.POST,
            instance=address
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Address updated successfully.'
            )

            return redirect(
                'addresses'
            )

    else:

        form = AddressForm(
            instance=address
        )

    return render(
        request,
        'accounts/edit_address.html',
        {
            'form': form
        }
    )

@login_required
def delete_address(
    request,
    address_id
):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    was_default = address.is_default

    address.delete()

    if was_default:

        next_address = Address.objects.filter(
            user=request.user
        ).order_by(
            'created_at'
        ).first()

        if next_address:

            next_address.is_default = True
            next_address.save()

    messages.success(
        request,
        'Address deleted successfully.'
    )

    return redirect(
        'addresses'
    )

@login_required
def set_default_address(
    request,
    address_id
):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    address.is_default = True

    address.save()

    messages.success(
        request,
        'Default address updated.'
    )

    return redirect(
        'addresses'
    )

@login_required
def change_email(request):

    if request.method == 'POST':

        form = ChangeEmailForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            new_email = form.cleaned_data[
                'new_email'
            ]

            otp = generate_otp()

            OTPVerification.objects.create(
                email=new_email,
                otp=otp,
                purpose='change_email'
            )

            send_mail(
                'Email Change OTP',
                f'Your OTP is: {otp}',
                settings.EMAIL_HOST_USER,
                [new_email],
                fail_silently=False
            )

            request.session[
                'change_email_new_email'
            ] = new_email

            messages.success(
                request,
                'OTP sent successfully.'
            )

            return redirect(
                'change_email_verify_otp'
            )

    else:

        form = ChangeEmailForm(
            user=request.user
        )

    return render(
        request,
        'accounts/change_email.html',
        {
            'form': form
        }
    )


@login_required
def change_email_verify_otp(request):

    new_email = request.session.get(
        'change_email_new_email'
    )

    if not new_email:

        return redirect(
            'change_email'
        )

    otp_record = OTPVerification.objects.filter(
        email=new_email,
        purpose='change_email'
    ).order_by(
        '-created_at'
    ).first()

    if not otp_record:

        messages.error(
            request,
            'OTP not found.'
        )

        return redirect(
            'change_email'
        )

    if request.method == 'POST':

        form = OTPVerificationForm(
            request.POST
        )

        if form.is_valid():

            entered_otp = form.cleaned_data[
                'otp'
            ]

            if entered_otp == otp_record.otp:

                old_email = request.user.email

                request.user.email = new_email
                request.user.save()

                send_mail(
                    'Email Address Changed',
                    (
                        f'Your account email '
                        f'has been changed.\n\n'
                        f'Previous Email: {old_email}\n'
                        f'New Email: {new_email}\n\n'
                        f'If this was not you, '
                        f'please contact us immediately.\n\n'
                        f'Email: support@readzone.com\n'
                        f'Phone: +91 9800000075'
                    ),
                    settings.EMAIL_HOST_USER,
                    [old_email],
                    fail_silently=False
                )

                otp_record.delete()

                del request.session[
                    'change_email_new_email'
                ]

                logout(request)

                messages.success(
                    request,
                    'Email changed successfully. '
                    'Please login using your new email.'
                )

                return redirect(
                    'login'
                )

            else:

                messages.error(
                    request,
                    'Invalid OTP.'
                )

    else:

        form = OTPVerificationForm()

    return render(
        request,
        'accounts/change_email_verify_otp.html',
        {
            'form': form
        }
    )
@login_required
def change_email_resend_otp(request):

    return redirect(
        'change_email'
    )