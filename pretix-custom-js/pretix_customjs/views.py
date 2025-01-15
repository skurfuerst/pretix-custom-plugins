import base64
import hmac
import logging
from collections import defaultdict
from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Exists, OuterRef
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import DeleteView, FormView, ListView, TemplateView
from django_scopes import scopes_disabled
from django.http import HttpResponse, HttpResponseNotFound
from i18nfield.forms import I18nFormField, I18nTextInput
from pretix import settings
from pretix.base.forms import SettingsForm
from pretix.base.models import (
    Event,
    Order,
    OrderPosition,
    OrderRefund,
    Question,
    SubEvent,
)
from pretix.base.views.metrics import unauthed_response
from pretix.base.views.tasks import AsyncAction
from pretix.control.permissions import EventPermissionRequiredMixin
from pretix.control.views import UpdateView
from pretix.control.views.event import EventSettingsFormView, EventSettingsViewMixin
from pretix.control.views.orders import OrderView
from pretix.multidomain.urlreverse import eventreverse
from pretix.presale.views import EventViewMixin
from pretix.presale.views.order import OrderDetailMixin

logger = logging.getLogger(__name__)


class CustomjsSettingsForm(SettingsForm):
    customjs__presale = forms.CharField(widget=forms.Textarea, required=False)

class SettingsView(EventSettingsViewMixin, EventSettingsFormView):
    model = Event
    form_class = CustomjsSettingsForm
    template_name = "pretix_customjs/settings.html"
    permission = "can_change_settings"
    # TODO: Set user public name field

    def get_success_url(self):
        return reverse(
            "plugins:pretix_customjs:control.customjs.settings",
            kwargs={
                "organizer": self.request.event.organizer.slug,
                "event": self.request.event.slug,
            },
        )


class FrontendView(View):
    def get(self, request, *args, **kwargs):
        if not self.request.event.settings.customjs__presale:
            response = HttpResponse("// none")
            response.headers["Content-Type"] = "application/javascript"    
            return response
        
        response = HttpResponse(self.request.event.settings.customjs__presale)
        response.headers["Content-Type"] = "application/javascript"
        
        return response