from django.urls import re_path
from pretix.multidomain import event_url

from .views import (
    SettingsView,
    FrontendView,
)

urlpatterns = [
    re_path(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/customjs/",
        SettingsView.as_view(),
        name="control.customjs.settings",
    ),
]


event_patterns = [
    event_url(r'^customjs/', FrontendView.as_view(), name='frontend'),
]
