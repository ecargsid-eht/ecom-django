from locale import currency
import random
import string
from importlib.resources import contents
from re import template
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest

from django.conf import settings
from core.forms import CouponForm, CheckoutForm
from .models import (
    Address,
    Coupon,
    Item,
    ItemVariation,
    OrderItem,
    Order,
    Payment,
    Variation,
)
from django.utils import timezone


razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
)


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"


class ItemDetailsView(DetailView):
    model = Item
    template_name = "product.html"
    slug_url_kwarg = "slug"

    def get_context_data(self, *args, **kwargs):
        context = super(ItemDetailsView, self).get_context_data(*args, **kwargs)
        context["items"] = Item.objects.exclude(slug=self.kwargs["slug"])
        return context


class AddToCart(LoginRequiredMixin, View):
    def get(self, request, slug, *args, **kwargs):
        item = get_object_or_404(Item, slug=slug)

        order_item, created = OrderItem.objects.get_or_create(
            item=item, user=request.user, ordered=False
        )
        # for varient
        var = []

        varient = Variation.objects.filter(item=item)

        for v in varient:
            var.append(request.GET.get(v.name, None))

        order_qs = Order.objects.filter(user=request.user, ordered=False)

        if order_qs.exists():
            order = order_qs[0]
            if order.items.filter(item__slug=item.slug).exists():
                order_item.qty += 1
                order_item.save()
                return redirect("core:order-summary")
            else:
                order.items.add(order_item)

                for v in var:
                    a = ItemVariation.objects.get(
                        value=v, variation__item__slug=item.slug
                    )
                    order_item.item_variations.add(a)
                return redirect("core:order-summary")

        else:
            ordered_date = timezone.now()
            order = Order.objects.create(user=request.user, start_date=ordered_date)
            order.items.add(order_item)
            return redirect("core:order-summary")


class MinusProduct(View, LoginRequiredMixin):
    def get(self, request, slug, *args, **kwargs):
        item = get_object_or_404(Item, slug=slug)

        order_item, created = OrderItem.objects.get_or_create(
            item=item, user=request.user, ordered=False
        )
        # for varient
        var = []

        varient = Variation.objects.filter(item=item)

        for v in varient:
            var.append(request.GET.get(v.name, None))

        order_qs = Order.objects.filter(user=request.user, ordered=False)

        if order_qs.exists():
            order = order_qs[0]
            if order.items.filter(item__slug=item.slug).exists():
                if order_item.qty > 1:
                    order_item.qty -= 1
                    order_item.save()
                return redirect("core:order-summary")
            else:
                order.items.add(order_item)

                for v in var:
                    a = ItemVariation.objects.get(
                        value=v, variation__item__slug=item.slug
                    )
                    order_item.item_variations.add(a)
                return redirect("core:order-summary")

        else:
            ordered_date = timezone.now()
            order = Order.objects.create(user=request.user, start_date=ordered_date)
            order.items.add(order_item)
            return redirect("core:order-summary")


class OrderSummaryVIew(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if order.items.count() < 1:
                return redirect("core:homepage")
            order_item = order.items.all()
            context = {"object": order, "couponform": CouponForm}
        except ObjectDoesNotExist:
            return redirect("core:homepage")

        return render(self.request, "order-summary.html", context)

    model = Order
    template_name = "order_summary.html"


class DeleteItem(View):
    def get(self, request, slug, *args, **kwargs):
        print("hi")
        item = OrderItem.objects.get(
            user=self.request.user, items__ordered=False, items__item__slug=slug
        )
        if item:
            if item.delete():
                return redirect("core:order-summary")


class RemoveFromCart(View, LoginRequiredMixin):
    def get(self, request, slug, *args, **kwargs):
        item = get_object_or_404(Item, slug=slug)

        order_qs = Order.objects.filter(user=request.user, ordered=False)

        if order_qs.exists():
            order = order_qs[0]
            if order.items.filter(item__slug=item.slug).exists():
                order_item = OrderItem.objects.filter(
                    item=item, user=request.user, ordered=False
                )[0]
                order.items.remove(order_item)
                order_item.delete()
            return redirect("core:order-summary")


def checkCoupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return True
    except ObjectDoesNotExist:
        return False


def getCoupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        return redirect("code:order-summary")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        if self.request.method == "POST":
            form = CouponForm(self.request.POST or None)
            if form.is_valid():
                try:
                    code = form.cleaned_data.get("code")
                    if checkCoupon(self.request, code):
                        order = Order.objects.get(user=self.request.user, ordered=False)
                        order.coupon = getCoupon(self.request, code)
                        order.save()
                        return redirect("core:order-summary")
                    else:
                        return redirect("core:order-summary")
                except ObjectDoesNotExist:
                    return redirect("core:order-summary")


class RemoveCouponView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        order.coupon = None
        order.save()
        return redirect("core:order-summary")


def create_ref_code():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=20))


class CheckOutView(View):
    def get(self, *args, **kwargs):
        address = Address.objects.filter(user=self.request.user)
        context = {}
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            amount = order.get_payable_amount() * 100
            currency = "INR"
            DATA = {
                "amount": amount,
                "currency": currency,
            }
            order_id = razorpay_client.order.create(data=DATA)

            context["order"] = order
            context["form"] = form
            context["address"] = address
            context["razorpay_key"] = settings.RAZOR_KEY_ID
            context["amount"] = order.get_payable_amount()
            context["order_id"] = order_id["id"]
            return render(
                self.request,
                "checkout.html",
                context=context,
            )
        except ObjectDoesNotExist:
            return redirect("core:homepage")

    def post(self, *args, **kwargs):
        if self.request.method == "POST":
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm(self.request.POST or None, use_required_attribute=False)
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                data = form.save(commit=False)
                data.user = self.request.user
                data.save()
                order.address = data
                order.save()
                # makePayment(self.request)
                return redirect("core:checkout")
            else:
                return redirect("core:checkout")
        else:
            return redirect("core:checkout")


def saved_address_action(r):
    if r.method == "POST":
        order = Order.objects.get(user=r.user, ordered=False)
        saved_address = r.POST.get("saved_address")
        selected_address = Address.objects.get(id=saved_address)
        order.address = selected_address
        order.save()
        # makePayment(r)


@csrf_exempt
def paymenthandler(request):

    # only accept POST request.
    if request.method == "POST":
        try:
            # print(request.POST.get("razorpay_payment_id"))
            # get the required parameters from post request.
            payment_id = request.POST.get("razorpay_payment_id", "")
            razorpay_order_id = request.POST.get("razorpay_order_id", "")
            signature = request.POST.get("razorpay_signature", "")
            params_dict = {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }
            print(params_dict)

            # verify the payment signature.
            result = razorpay_client.utility.verify_payment_signature(params_dict)
            if result is None:  # set None to True
                order = Order.objects.get(user=request.user, ordered=False)
                amount = order.get_payable_amount() * 100
                try:
                    # capture the payemt
                    razorpay_client.payment.capture(payment_id, amount)
                    payment = Payment()
                    payment.txt_id = "234565432345"
                    payment.user = request.user
                    payment.amount = order.get_payable_amount()

                    payment.save()

                    # assign the payment in order

                    order_item = order.items.all()
                    order_item.update(ordered=True)
                    order.ordered = True
                    order.payment = payment
                    order.ref_code = create_ref_code()
                    order.save()

                    # render success page on successful caputre of payment
                    return render(request, "paymentsuccess.html")

                except:

                    # if there is an error while capturing payment.
                    return render(request, "paymentfail.html")
            else:

                # if signature verification fails.
                return render(request, "paymentfail.html")
        except:

            # if we don't find the required parameters in POST data
            print("parameter issue")
            return HttpResponseBadRequest()
    else:
        print("post method issue")
        # if other than POST request is made.
        return HttpResponseBadRequest()


def myOrder(r):
    order = Order.objects.filter(user=r.user, ordered=True)
    return render(r, "myorder.html", {"order": order})
