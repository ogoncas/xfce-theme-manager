from gi.repository import GLib

from ..config import custom_folders
from ..i18n import _
from ..paths import DEFAULT_ICON_DIRS
from .common import BackendError, ensure_searchable, find_theme_path, list_theme_dirs, xfconf_get, xfconf_set


# Cursor themes live in the icon folders; they are the ones with a "cursors" subfolder
def _cursor_dirs():
    return DEFAULT_ICON_DIRS + custom_folders("icon_theme_folders")


def get_cursor_themes():
    return list_theme_dirs(_cursor_dirs(), "cursors")


def get_current_cursor_theme():
    return xfconf_get("xsettings", "/Gtk/CursorThemeName")


def set_cursor_theme(name):
    path = find_theme_path(name, _cursor_dirs(), "cursors")
    if path is None:
        raise BackendError(_("err_cursor_missing", name=name))
    ensure_searchable(path, DEFAULT_ICON_DIRS, GLib.build_filenamev([GLib.get_user_data_dir(), "icons"]))
    try:
        xfconf_set("xsettings", "/Gtk/CursorThemeName", name)
    except BackendError as e:
        raise BackendError(_("err_cursor_apply", detail=str(e))) from e
