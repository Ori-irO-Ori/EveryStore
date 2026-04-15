import logging
import urllib.request
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_order_confirmation(order):
    """
    Send an HTML order confirmation email to the buyer.
    Silently logs and skips if email is not configured.
    """
    if not settings.EMAIL_HOST_USER:
        return

    # Pull contact info from SiteSettings (with .env fallback)
    try:
        from store.models import SiteSettings
        site = SiteSettings.get()
        contact_type = site.contact_type
        contact_value = site.contact_value
    except Exception:
        contact_type = settings.SELLER_CONTACT_TYPE
        contact_value = settings.SELLER_CONTACT_VALUE

    context = {
        'order': order,
        'store_name': settings.STORE_NAME,
        'primary_color': settings.THEME_PRIMARY_COLOR,
        'contact_type': contact_type,
        'contact_value': contact_value,
    }

    subject = f'Order Confirmed — {order.order_number} | {settings.STORE_NAME}'

    # Use custom email template from S3 if uploaded, otherwise fall back to default
    html_body = None
    try:
        from store.models import SiteSettings
        site = SiteSettings.get()
        if site.custom_email_template:
            with urllib.request.urlopen(site.custom_email_template.url) as resp:
                raw_html = resp.read().decode('utf-8')
            html_body = Template(raw_html).render(Context(context))
    except Exception as e:
        logger.warning('Could not load custom email template, using default: %s', e)

    if html_body is None:
        html_body = render_to_string('emails/order_confirmation.html', context)

    # Plain-text fallback
    text_body = (
        f'Hi {order.first_name},\n\n'
        f'Your order {order.order_number} is confirmed!\n\n'
        f'Total: ${order.total_amount}\n\n'
        + (f'Questions? Contact us via {contact_type}: {contact_value}\n\n' if contact_value else '')
        + f'— {settings.STORE_NAME}'
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
        logger.info('Order confirmation sent to %s for order %s', order.email, order.order_number)
    except Exception as e:
        # Never let email errors break the payment success flow
        logger.error('Failed to send order confirmation for %s: %s', order.order_number, e)
