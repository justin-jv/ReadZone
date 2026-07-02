from django.urls import path
from . import views

urlpatterns = [

    path('shop/', views.shop, name='shop'),
    path('shop/<slug:slug>/', views.product_detail, name='product_detail'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/increase/<int:item_id>/', views.increase_quantity, name='increase_quantity'),
    path('cart/decrease/<int:item_id>/', views.decrease_quantity, name='decrease_quantity'),

    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-success/<str:order_id>/', views.order_success, name='order_success'),

    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-orders/<str:order_id>/', views.order_detail, name='order_detail'),

    path('cancel-item/<int:item_id>/', views.cancel_order_item, name='cancel_order_item'),

    path('return-item/<int:item_id>/', views.return_order_item, name='return_order_item'),

    path('invoice/<str:order_id>/', views.download_invoice, name='download_invoice'),

    path('wallet/', views.wallet, name='wallet'),

    # path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    # path('remove-coupon/', views.remove_coupon, name='remove_coupon'),

    path('apply-coupon/<int:coupon_id>/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    

    path('create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('verify-razorpay-payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    
    
]