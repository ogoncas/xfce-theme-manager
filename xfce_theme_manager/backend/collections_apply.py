from ..i18n import _
from .common import BackendError
from .gtk import set_gtk_theme
from .icons import set_icon_theme
from .mousepad import set_mousepad_theme
from .rofi import set_rofi_theme
from .wallpaper import set_wallpaper


def apply_collection(col_data):
    steps = (
        ("gtk", "label_gtk", set_gtk_theme),
        ("icon", "label_icons", set_icon_theme),
        ("wallpaper", "label_wallpaper", set_wallpaper),
        ("rofi", "label_rofi", set_rofi_theme),
        ("mousepad", "label_mousepad", set_mousepad_theme),
    )
    # Run every step and report all failures together
    errors = []
    for key, label_key, setter in steps:
        value = col_data.get(key)
        if not value:
            continue
        try:
            setter(value)
        except Exception as e:
            errors.append(f"{_(label_key)} {e}")

    if errors:
        raise BackendError("\n".join(errors))
