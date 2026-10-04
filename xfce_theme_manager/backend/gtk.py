import os

from gi.repository import GLib

from ..config import custom_folders
from ..i18n import _
from ..paths import DEFAULT_GTK_DIRS
from .common import BackendError, ensure_searchable, find_theme_path, list_theme_dirs, xfconf_get, xfconf_set


def get_gtk_themes():
    return list_theme_dirs(DEFAULT_GTK_DIRS + custom_folders("gtk_theme_folders"), "gtk-3.0")


def get_current_gtk_theme():
    return xfconf_get("xsettings", "/Net/ThemeName")


def set_gtk_theme(name):
    path = find_theme_path(name, DEFAULT_GTK_DIRS + custom_folders("gtk_theme_folders"), "gtk-3.0")
    if path:
        ensure_searchable(path, DEFAULT_GTK_DIRS, os.path.join(GLib.get_user_data_dir(), "themes"))
    try:
        xfconf_set("xsettings", "/Net/ThemeName", name)
        # Only switch the xfwm4 theme if it ships window decorations, otherwise borders break
        if path is None or os.path.isdir(os.path.join(path, "xfwm4")):
            xfconf_set("xfwm4", "/general/theme", name)
    except BackendError as e:
        raise BackendError(_("err_gtk_apply", detail=str(e))) from e
