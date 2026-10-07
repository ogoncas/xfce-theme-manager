import os

from gi.repository import GLib

from ..fileio import atomic_write_text
from ..i18n import _
from .common import BackendError, xfconf_get, xfconf_set


TERMINAL_RC = os.path.join(GLib.get_user_config_dir(), "xfce4", "terminal", "terminalrc")
TERMINAL_SECTION = "[Configuration]"


def _clean_font(value):
    value = (value or "").strip()
    if not value or len(value) > 200 or any(ord(c) < 32 for c in value):
        raise BackendError(_("err_font_invalid"))
    return value


def _set_xfconf_font(channel, prop, value):
    value = _clean_font(value)
    try:
        xfconf_set(channel, prop, value)
    except BackendError as e:
        raise BackendError(_("err_font_apply", detail=str(e))) from e


def get_interface_font():
    return xfconf_get("xsettings", "/Gtk/FontName")


def set_interface_font(value):
    _set_xfconf_font("xsettings", "/Gtk/FontName", value)


def get_title_font():
    return xfconf_get("xfwm4", "/general/title_font")


def set_title_font(value):
    _set_xfconf_font("xfwm4", "/general/title_font", value)


def get_monospace_font():
    return xfconf_get("xsettings", "/Gtk/MonospaceFontName")


def set_monospace_font(value):
    _set_xfconf_font("xsettings", "/Gtk/MonospaceFontName", value)


def _read_terminal_rc():
    try:
        with open(TERMINAL_RC, encoding="utf-8") as f:
            return f.read().splitlines()
    except OSError:
        return []


def _keyfile_get(lines, key):
    in_section = False
    for line in lines:
        text = line.strip()
        if text.startswith("["):
            in_section = text == TERMINAL_SECTION
        elif in_section and text.startswith(key + "="):
            return text.split("=", 1)[1]
    return None


def _keyfile_set(lines, key, value):
    out = list(lines)
    start = next((i for i, line in enumerate(out) if line.strip() == TERMINAL_SECTION), None)
    if start is None:
        if out and out[-1].strip():
            out.append("")
        return out + [TERMINAL_SECTION, f"{key}={value}"]

    end = len(out)
    for i in range(start + 1, len(out)):
        if out[i].strip().startswith("["):
            end = i
            break
    for i in range(start + 1, end):
        if out[i].strip().startswith(key + "="):
            out[i] = f"{key}={value}"
            return out

    # Insert after the last non-blank line of the section
    pos = end
    while pos > start + 1 and not out[pos - 1].strip():
        pos -= 1
    out.insert(pos, f"{key}={value}")
    return out


def get_terminal_font():
    """Font Xfce Terminal is using: its own setting, or the system monospace font."""
    lines = _read_terminal_rc()
    name = _keyfile_get(lines, "FontName")
    use_system = (_keyfile_get(lines, "FontUseSystem") or "TRUE").upper()
    if name and use_system == "FALSE":
        return name
    return get_monospace_font()


def set_terminal_font(value):
    value = _clean_font(value)
    lines = _keyfile_set(_read_terminal_rc(), "FontName", value)
    lines = _keyfile_set(lines, "FontUseSystem", "FALSE")
    try:
        atomic_write_text(TERMINAL_RC, "\n".join(lines) + "\n")
    except OSError as e:
        raise BackendError(_("err_font_apply", detail=str(e))) from e


# (key, getter, setter): the key also names the "font_<key>" label
FONT_TARGETS = (
    ("interface", get_interface_font, set_interface_font),
    ("title", get_title_font, set_title_font),
    ("monospace", get_monospace_font, set_monospace_font),
    ("terminal", get_terminal_font, set_terminal_font),
)
