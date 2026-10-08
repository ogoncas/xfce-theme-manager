import os
import re

from gi.repository import GLib

from ..config import custom_folders
from ..fileio import atomic_write_text
from ..i18n import _
from ..paths import DEFAULT_ROFI_DIRS
from .common import BackendError


ROFI_CONFIG = os.path.join(GLib.get_user_config_dir(), "rofi", "config.rasi")
_ROFI_THEME_RE = re.compile(r'^[ \t]*@theme[ \t]+(?:"((?:[^"\\\n]|\\.)+)"|([^\s"]+))', re.MULTILINE)


def get_rofi_themes():
    by_name = {}
    for d in DEFAULT_ROFI_DIRS + custom_folders("rofi_theme_folders"):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for f in names:
            if f.endswith(".rasi"):
                # On duplicate names the first folder wins (user before system)
                by_name.setdefault(f, os.path.join(d, f))
    return [by_name[k] for k in sorted(by_name, key=str.lower)]


def get_current_rofi_theme():
    try:
        with open(ROFI_CONFIG, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return None
    m = _ROFI_THEME_RE.search(content)
    if not m:
        return None
    if m.group(1):
        return re.sub(r"\\(.)", r"\1", m.group(1))
    return m.group(2)


# `current` can be a path, start with ~, or be just the theme name
def rofi_theme_matches(item, current):
    if not current:
        return False
    cur = os.path.expanduser(current.strip())
    if item == cur:
        return True
    if os.path.dirname(cur):
        try:
            return os.path.samefile(item, cur)
        except OSError:
            return False
    stem = cur[:-5] if cur.endswith(".rasi") else cur
    return os.path.basename(item)[:-5] == stem


def set_rofi_theme(theme_path):
    escaped = theme_path.replace("\\", "\\\\").replace('"', '\\"')
    theme_line = '@theme "{}"'.format(escaped)
    try:
        try:
            with open(ROFI_CONFIG, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except FileNotFoundError:
            content = None
        if content is None:
            content = "configuration {\n}\n\n" + theme_line + "\n"
        else:
            pattern = re.compile(r"^[ \t]*@theme\b.*$", re.MULTILINE)
            if pattern.search(content):
                content = pattern.sub(lambda m: theme_line, content)
            else:
                content = theme_line + "\n" + content
        atomic_write_text(ROFI_CONFIG, content)
    except OSError as e:
        raise BackendError(_("err_rofi_apply", detail=str(e))) from e
