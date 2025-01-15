# Register your receivers here
from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _
from django.template.loader import get_template
from pretix.control.signals import (
    nav_event_settings
)
from pretix.presale.signals import html_footer
from pretix.base.signals import register_invoice_renderers

@receiver(html_footer, dispatch_uid="pretix_customjs_html_footer")
def html_foot_presale(sender, request=None, **kwargs):
    template = get_template("pretix_customjs/presale_footer.html")
    return template.render({"event": request.event})


@receiver(nav_event_settings, dispatch_uid="customjs_nav")
def customjs_nav_event(sender, request=None, **kwargs):
    url = resolve(request.path_info)
    if not request.user.has_event_permission(
        request.organizer, request.event, "can_change_settings", request=request
    ):
        return []
    return [
        {
            "label": _("Custom JS"),
            "url": reverse(
                "plugins:pretix_customjs:control.customjs.settings",
                kwargs={
                    "event": request.event.slug,
                    "organizer": request.event.organizer.slug,
                },
            ),
            "active": (
                url.namespace == "plugins:pretix_customjs"
            ),
        }
    ]


@receiver(register_invoice_renderers, dispatch_uid="output_custom")
def register_invoice_renderers(sender, **kwargs):
    from .invoice.MyInvoiceRenderer import MyInvoiceRenderer
    return MyInvoiceRenderer
