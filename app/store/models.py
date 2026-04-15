from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='products'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Original price before discount (shown as strikethrough)'
    )
    stock = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text='Show on homepage')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if not img:
            img = self.images.first()
        return img

    @property
    def discount_percent(self):
        if self.compare_price and self.compare_price > self.price:
            return int((1 - self.price / self.compare_price) * 100)
        return None


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    # Images are stored in S3 when S3_BUCKET is configured in .env
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product.name} — image {self.id}'


class SiteSettings(models.Model):
    """
    Singleton model — only one row (pk=1) ever exists.
    Managed entirely from the admin panel.
    """

    CONTACT_TYPE_CHOICES = [
        ('email',     'Email'),
        ('discord',   'Discord'),
        ('wechat',    'WeChat'),
        ('telegram',  'Telegram'),
        ('whatsapp',  'WhatsApp'),
        ('line',      'LINE'),
        ('instagram', 'Instagram'),
        ('twitter',   'Twitter / X'),
        ('facebook',  'Facebook'),
        ('other',     _('Other')),
    ]

    # ── Contact ──────────────────────────────────────────────────────────
    contact_type = models.CharField(
        max_length=20, choices=CONTACT_TYPE_CHOICES, default='email',
        verbose_name=_('Contact type'),
    )
    contact_value = models.CharField(
        max_length=300, blank=True,
        verbose_name=_('Contact value'),
        help_text=_('Email address, Discord tag, WeChat ID, Telegram @username, etc.'),
    )
    contact_label = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Display label (optional)'),
        help_text=_('Custom text shown on the button, e.g. "Chat with us". Leave blank to use the type name.'),
    )

    # ── Custom Email Template ─────────────────────────────────────────────
    custom_email_template = models.FileField(
        upload_to='site/email/',
        blank=True, null=True,
        verbose_name=_('Custom order confirmation email (HTML)'),
        help_text=_(
            'Upload an HTML file to replace the default order confirmation email. '
            'Use {{ order }}, {{ store_name }}, {{ primary_color }} as template variables. '
            'Delete to revert to the default template.'
        ),
    )

    # ── Custom Homepage ───────────────────────────────────────────────────
    custom_homepage = models.FileField(
        upload_to='site/homepage/',
        blank=True, null=True,
        verbose_name=_('Custom homepage (index.html)'),
        help_text=_(
            'Upload an HTML file to completely replace the default homepage. '
            'Stored in S3. Delete the file here to revert to the default homepage. '
            'The HTML can reference any external CSS/JS/images freely.'
        ),
    )

    class Meta:
        verbose_name = _('Site Settings')
        verbose_name_plural = _('Site Settings')

    def __str__(self):
        return 'Site Settings'

    @classmethod
    def get(cls):
        """Always returns the single settings object, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
