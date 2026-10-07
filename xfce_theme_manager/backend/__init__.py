from .collections_apply import apply_collection
from .common import BackendError
from .fonts import FONT_TARGETS
from .gtk import get_current_gtk_theme, get_gtk_themes, set_gtk_theme
from .icons import get_current_icon_theme, get_icon_themes, set_icon_theme
from .mousepad import get_current_mousepad_theme, get_mousepad_themes, set_mousepad_theme
from .rofi import get_current_rofi_theme, get_rofi_themes, rofi_theme_matches, set_rofi_theme
from .wallpaper import get_current_wallpaper, scan_wallpaper_images, set_wallpaper
from .xfwm import collection_xfwm, get_current_xfwm_theme, get_xfwm_themes, set_xfwm_theme

__all__ = [
    "BackendError", "apply_collection", "scan_wallpaper_images", "FONT_TARGETS",
    "get_gtk_themes", "get_current_gtk_theme", "set_gtk_theme",
    "get_xfwm_themes", "get_current_xfwm_theme", "set_xfwm_theme", "collection_xfwm",
    "get_icon_themes", "get_current_icon_theme", "set_icon_theme",
    "get_mousepad_themes", "get_current_mousepad_theme", "set_mousepad_theme",
    "get_rofi_themes", "get_current_rofi_theme", "rofi_theme_matches", "set_rofi_theme",
    "get_current_wallpaper", "set_wallpaper",
]
