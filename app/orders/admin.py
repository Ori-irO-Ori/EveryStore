from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Order, OrderItem


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'product_price', 'quantity', 'line_total')
    can_delete = False

    def line_total(self, obj):
        if not obj.pk:
            return '—'
        return f'${obj.line_total:.2f}'
    line_total.short_description = 'Total'


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        'order_number', 'full_name', 'email', 'status',
        'total_amount', 'created_at'
    )
    list_filter = ('status', 'created_at', 'country')
    search_fields = ('order_number', 'email', 'first_name', 'last_name')
    readonly_fields = (
        'order_number', 'paypal_order_id',
        'created_at', 'updated_at', 'total_amount'
    )
    inlines = [OrderItemInline]
    list_per_page = 25

    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'status', 'total_amount', 'paypal_order_id')
        }),
        ('Customer', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Shipping Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code')
        }),
        ('Note', {
            'fields': ('note',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
