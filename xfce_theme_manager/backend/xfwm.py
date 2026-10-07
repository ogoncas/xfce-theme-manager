import os

from gi.repository import GLib

from ..config import custom_folders
from ..i18n import _
from ..paths import DEFAULT_GTK_DIRS
from .common import BackendError, ensure_searchable, find_theme_path, list_theme_dirs, xfconf_get, xfconf_set


# Window decorations live in <theme>/xfwm4/themerc, in the same folders as GTK themes
XFWM_MARKER = os.path.join("xfwm4", "themerc")


def _theme_dirs():
    return DEFAULT_GTK_DIRS + custom_folders("gtk_theme_folders")


def get_xfwm_themes():
    return list_theme_dirs(_theme_dirs(), XFWM_MARKER)


def get_current_xfwm_theme():
    return xfconf_get("xfwm4", "/general/theme")


def xfwm_theme_available(name):
    return find_theme_path(name, _theme_dirs(), XFWM_MARKER) is not None


def set_xfwm_theme(name):
    path = find_theme_path(name, _theme_dirs(), XFWM_MARKER)
    if path is None:
        raise BackendError(_("err_xfwm_missing", name=name))
    ensure_searchable(path, DEFAULT_GTK_DIRS, os.path.join(GLib.get_user_data_dir(), "themes"))
    try:
        xfconf_set("xfwm4", "/general/theme", name)
    except BackendError as e:
        raise BackendError(_("err_xfwm_apply", detail=str(e))) from e


def collection_xfwm(col_data):
    """XFWM theme a collection applies. Older collections reused the GTK theme."""
    if "xfwm" in col_data:
        return col_data["xfwm"] or None
    gtk = col_data.get("gtk")
    return gtk if gtk and xfwm_theme_available(gtk) else None
