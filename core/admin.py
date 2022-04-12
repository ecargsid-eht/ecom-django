from argparse import Action
from django.contrib import admin
from .models import *

def make_accepted_refund(modeladmin, request, queryset):
    queryset.update(refund_required=False,refund_granted=True)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user','ordered','being_delivered','recieved','refund_required','refund_granted','address','payment','coupon']

    list_display_links = ["user","address","payment","coupon"]

    list_filter = ['ordered','being_delivered','recieved','refund_required','refund_granted']

    search_fields = ['user__username','ref_code']

    actions = [make_accepted_refund]    



admin.site.register(Item)
admin.site.register(Category)
admin.site.register(Coupon)
admin.site.register(Brand)
admin.site.register(Address)
admin.site.register(Payment)
admin.site.register(Order,OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Refund) 
admin.site.register(Variation)
admin.site.register(ItemVariation)


# Register your models here.
