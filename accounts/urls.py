from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),

    path('signup/', views.signup, name='signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('forgot-password-verify-otp/', views.forgot_password_verify_otp, name='forgot_password_verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('forgot-password-resend-otp/', views.forgot_password_resend_otp, name='forgot_password_resend_otp'),

    path('change-password/', views.change_password, name='change_password'),

    path('addresses/', views.addresses, name='addresses'),
    path('addresses/add/', views.add_address, name='add_address'),
    path('addresses/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('addresses/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('addresses/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),

    path('change-email/', views.change_email, name='change_email'),
    path('change-email-verify-otp/', views.change_email_verify_otp, name='change_email_verify_otp'),
    path('change-email-resend-otp/', views.change_email_resend_otp, name='change_email_resend_otp'),
    

]
