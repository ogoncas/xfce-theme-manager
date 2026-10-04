from gi.repository import GLib

from .config import load_config
from .locales.en import EN
from .locales.pt_br import PT_BR


TRANSLATIONS = {"en": EN, "pt_BR": PT_BR}


def detect_system_language():
    """Return 'pt_BR' if the user's language list prefers Portuguese, else 'en'."""
    for name in GLib.get_language_names():
        low = name.lower()
        if low.startswith("pt"):
            return "pt_BR"
        if low.startswith("en"):
            return "en"
    return "en"


class I18N:
    def __init__(self):
        self.current = "en"
        self.apply_language(load_config().get("language", "auto"))

    def apply_language(self, lang_setting):
        if lang_setting == "auto" or lang_setting not in TRANSLATIONS:
            self.current = detect_system_language()
        else:
            self.current = lang_setting

    def t(self, key, **kwargs):
        table = TRANSLATIONS.get(self.current, EN)
        text = table.get(key, EN.get(key, key))
        if not kwargs:
            return text
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text


i18n = I18N()
_ = i18n.t
