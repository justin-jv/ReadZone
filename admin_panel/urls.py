from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('users/', views.user_management, name='user_management'),

    path('users/block/<int:user_id>/', views.block_user, name='block_user'),
    path('users/unblock/<int:user_id>/', views.unblock_user, name='unblock_user'),

    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),

    path('categories/', views.category_management, name='category_management'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:category_id>/', views.edit_category, name='edit_category'),
    path('categories/deactivate/<int:category_id>/', views.deactivate_category, name='deactivate_category'),
    path('categories/activate/<int:category_id>/', views.activate_category, name='activate_category'),

    path('languages/', views.language_management, name='language_management'),
    path('languages/add/', views.add_language, name='add_language'),
    path('languages/edit/<int:language_id>/', views.edit_language, name='edit_language'),
    path('languages/deactivate/<int:language_id>/', views.deactivate_language, name='deactivate_language'),
    path('languages/activate/<int:language_id>/', views.activate_language, name='activate_language'),

    path('products/', views.product_management, name='product_management'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/deactivate/<int:product_id>/', views.deactivate_product, name='deactivate_product'),
    path('products/activate/<int:product_id>/', views.activate_product, name='activate_product'),

    path('products/image/delete/<int:image_id>/', views.delete_product_image, name='delete_product_image'),

    path('orders/', views.order_management, name='order_management'),
    path('orders/<str:order_id>/', views.order_detail_admin, name='order_detail_admin'),
    path('orders/item/<int:item_id>/status/', views.update_order_item_status, name='update_order_item_status'),
    path('orders/item/<int:item_id>/approve-return/', views.approve_return, name='approve_return'),

    path('coupons/', views.coupon_management, name='coupon_management'),
    path('coupons/add/', views.add_coupon, name='add_coupon'),
    path('coupons/delete/<int:coupon_id>/', views.delete_coupon, name='delete_coupon'),

    path('product-offers/', views.product_offer_management, name='product_offer_management'),
    path('product-offers/add/', views.add_product_offer, name='add_product_offer'),
    path('product-offers/edit/<int:offer_id>/', views.edit_product_offer, name='edit_product_offer'),
    path('product-offers/toggle/<int:offer_id>/', views.toggle_product_offer, name='toggle_product_offer'),
    
    path('category-offers/', views.category_offer_management, name='category_offer_management'),
    path('category-offers/add/', views.add_category_offer, name='add_category_offer'),
    path('category-offers/edit/<int:offer_id>/', views.edit_category_offer, name='edit_category_offer'),
    path('category-offers/toggle/<int:offer_id>/', views.toggle_category_offer, name='toggle_category_offer'),
            
    
]
