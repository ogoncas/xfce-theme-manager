import os
import re

from gi.repository import Gio, GLib

from ..config import custom_folders
from ..fileio import atomic_write_text
from ..i18n import _
from ..paths import xdg_data_dirs
from .common import BackendError


MOUSEPAD_SCHEMA = "org.xfce.mousepad.preferences.view"
MOUSEPAD_KEY = "color-scheme"
_STYLE_ID_RE = re.compile(r'<style-scheme\b[^>]*?\bid\s*=\s*"([^"]+)"', re.DOTALL)


def _mousepad_style_dirs():
    dirs = []
    for base in xdg_data_dirs():
        try:
            names = sorted(os.listdir(base))
        except OSError:
            continue
        for n in names:
            if n.startswith("gtksourceview-"):
                dirs.append(os.path.join(base, n, "styles"))
    return dirs + custom_folders("mousepad_style_folders")


# The scheme id is what Mousepad stores; it can differ from the file name
def _style_scheme_id(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.read(4096)
    except OSError:
        return None
    m = _STYLE_ID_RE.search(head)
    return m.group(1) if m else os.path.splitext(os.path.basename(path))[0]


def get_mousepad_themes():
    themes = set()
    for d in _mousepad_style_dirs():
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for f in names:
            if f.endswith(".xml"):
                scheme = _style_scheme_id(os.path.join(d, f))
                if scheme:
                    themes.add(scheme)
    return sorted(themes, key=str.lower)


# Gio.Settings.new() aborts if the schema is missing, so look it up first
def _mousepad_settings():
    source = Gio.SettingsSchemaSource.get_default()
    if source is None:
        return None
    schema = source.lookup(MOUSEPAD_SCHEMA, True)
    if schema is None or not schema.has_key(MOUSEPAD_KEY):
        return None
    return Gio.Settings.new(MOUSEPAD_SCHEMA)


def _mousepadrc_path():
    return os.path.join(GLib.get_user_config_dir(), "Mousepad", "mousepadrc")


def get_current_mousepad_theme():
    settings = _mousepad_settings()
    if settings is not None:
        return settings.get_string(MOUSEPAD_KEY) or None

    try:
        # Fallback for old Mousepad versions without GSettings
        with open(_mousepadrc_path(), encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("color-scheme="):
                    return line.split("=", 1)[1].strip().strip("'\"") or None
    except OSError:
        pass
    return None


def set_mousepad_theme(theme_name):
    settings = _mousepad_settings()
    if settings is not None:
        if not settings.set_string(MOUSEPAD_KEY, theme_name):
            raise BackendError(_("err_mousepad_apply", detail=MOUSEPAD_KEY))
        Gio.Settings.sync()
        return

    rc_path = _mousepadrc_path()
    try:
        with open(rc_path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []
    except OSError as e:
        raise BackendError(_("err_mousepad_apply", detail=str(e))) from e

    new_lines = []
    replaced = False
    for line in lines:
        if line.lower().startswith("color-scheme="):
            new_lines.append(f"color-scheme={theme_name}\n")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"color-scheme={theme_name}\n")
    try:
        atomic_write_text(rc_path, "".join(new_lines))
    except OSError as e:
        raise BackendError(_("err_mousepad_apply", detail=str(e))) from e
