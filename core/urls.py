from django.urls import path
from .views import *


app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="homepage"),
    path("products/<slug>/", ItemDetailsView.as_view(), name="item"),
    path("order-summary/", OrderSummaryVIew.as_view(), name="order-summary"),
    path("add-to-cart/<slug>/", AddToCart.as_view(), name="add-to-cart"),
    path("delete-item/<slug>/", RemoveFromCart.as_view(), name="delete-item"),
    path("minus-item/<slug>/", MinusProduct.as_view(), name="minus-item"),
    path("add-coupon/", AddCouponView.as_view(), name="add-coupon"),
    path("remove-coupon/", RemoveCouponView.as_view(), name="remove-coupon"),
    path("checkout/", CheckOutView.as_view(), name="checkout"),
    path("checkout/paymenthandler/", paymenthandler, name="paymenthandler"),
    # path("make-payment/", makePayment, name="makePayment"),
    path("saved-address-checkout/", saved_address_action, name="saved_address_action"),
    path("my-order/", myOrder, name="my_order"),
]
