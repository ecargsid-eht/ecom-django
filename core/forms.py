from django import forms

from core.models import Address
class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
    'class':"form-control",
    "placeholder":"Promo Code"
    }))  


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ["user"]