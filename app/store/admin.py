from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import UserCreationForm as UnfoldUserCreationForm
from unfold.forms import UserChangeForm as UnfoldUserChangeForm
from .models import Category, Product, ProductImage, SiteSettings

# Remove Groups entirely
admin.site.unregister(Group)

# Re-register User with unfold styling
User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    add_form = UnfoldUserCreationForm
    form = UnfoldUserChangeForm
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px;" />',
                obj.image.url
            )
        return '—'
    image_preview.short_description = 'Preview'


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'product_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def product_count(self, obj):
        return obj.products.filter(is_available=True).count()
    product_count.short_description = 'Active Products'


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = (
        'thumbnail', 'name', 'category', 'price', 'stock',
        'is_available', 'is_featured', 'updated_at'
    )
    list_display_links = ('thumbnail', 'name')
    list_filter = ('is_available', 'is_featured', 'category')
    list_editable = ('is_available', 'is_featured', 'stock')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'compare_price', 'stock')
        }),
        ('Visibility', {
            'fields': ('is_available', 'is_featured')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def thumbnail(self, obj):
        img = obj.primary_image
        if img:
            return format_html(
                '<img src="{}" style="height:48px;width:48px;object-fit:cover;border-radius:6px;" />',
                img.image.url
            )
        return format_html('<span style="color:#999">No image</span>')
    thumbnail.short_description = ''


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    list_display = ('image_preview', 'product', 'is_primary', 'order')
    list_filter = ('is_primary',)
    search_fields = ('product__name',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:48px;border-radius:4px;" />',
                obj.image.url
            )
        return '—'
    image_preview.short_description = 'Image'


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ('Contact', {
            'description': 'Shown to visitors when they click the contact button. No auto-redirect — just displays the info.',
            'fields': ('contact_type', 'contact_value', 'contact_label'),
        }),
        ('Email Template', {
            'description': (
                'Upload an HTML file to replace the default order confirmation email. '
                'Available variables: {{ order }}, {{ store_name }}, {{ primary_color }}, '
                '{{ contact_type }}, {{ contact_value }}. Delete to revert to the default.'
            ),
            'fields': ('custom_email_template',),
        }),
        ('Custom Homepage', {
            'description': (
                'Upload an index.html to replace the default homepage. '
                'Stored in S3. Remove the file to revert to the default homepage.'
            ),
            'fields': ('custom_homepage',),
        }),
    )

    def has_add_permission(self, request):
        # Only allow one row
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Redirect list view directly to the single settings object
        obj, _ = SiteSettings.objects.get_or_create(pk=1)
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(
            reverse(f'admin:store_sitesettings_change', args=[obj.pk])
        )
