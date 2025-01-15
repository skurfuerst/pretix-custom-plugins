from django.utils.translation import gettext_lazy
from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_customjs"
    verbose_name = "Custom JS"

    class PretixPluginMeta:
        name = gettext_lazy("Custom JS")
        author = "Sebastian Kurfürst"
        description = gettext_lazy("Short description")
        visible = True
        version = __version__
        category = "CUSTOMIZATION"
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


