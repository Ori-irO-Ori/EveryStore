from django.conf import settings


def store_settings(request):
    """
    Injects store-wide settings into every template context.
    Contact info comes from SiteSettings (DB), theme/name from .env.
    """
    # Lazy import to avoid circular imports at startup
    try:
        from .models import SiteSettings
        site = SiteSettings.get()
        contact_type = site.contact_type
        contact_value = site.contact_value
        contact_label = site.contact_label or site.get_contact_type_display()
    except Exception:
        # Fallback to .env values if DB not ready yet
        contact_type = settings.SELLER_CONTACT_TYPE
        contact_value = settings.SELLER_CONTACT_VALUE
        contact_label = settings.SELLER_CONTACT_TYPE.capitalize()

    return {
        'STORE_NAME': settings.STORE_NAME,
        'STORE_CURRENCY': settings.STORE_CURRENCY,
        'THEME_PRIMARY_COLOR': settings.THEME_PRIMARY_COLOR,
        'THEME_LOGO_URL': settings.THEME_LOGO_URL,
        'THEME_HERO_IMAGE_URL': settings.THEME_HERO_IMAGE_URL,
        # Contact — from DB (SiteSettings)
        'SELLER_CONTACT_TYPE': contact_type,
        'SELLER_CONTACT_VALUE': contact_value,
        'SELLER_CONTACT_LABEL': contact_label,
    }
