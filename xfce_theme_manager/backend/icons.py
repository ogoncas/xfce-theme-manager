import os
import re

from gi.repository import GLib

from ..config import custom_folders
from ..i18n import _
from ..paths import DEFAULT_ICON_DIRS
from .common import BackendError, ensure_searchable, find_theme_path, xfconf_get, xfconf_set


def get_icon_themes():
    dirs = DEFAULT_ICON_DIRS + custom_folders("icon_theme_folders")
    themes = set()
    for d in dirs:
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for name in names:
            if name.startswith(".") or name == "hicolor":
                continue
            index = os.path.join(d, name, "index.theme")
            if not os.path.isfile(index):
                continue
            try:
                with open(index, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "[Icon Theme]" not in content:
                continue
            if re.search(r"^Hidden\s*=\s*true\s*$", content, re.MULTILINE | re.IGNORECASE):
                continue
            # Skip cursor-only themes
            dirs_match = re.search(r"^Directories=(.*)$", content, re.MULTILINE)
            if dirs_match:
                subdirs = [s for s in dirs_match.group(1).split(",") if s]
                if subdirs and all("cursor" in s.lower() for s in subdirs):
                    continue
            themes.add(name)
    return sorted(themes, key=str.lower)


def get_current_icon_theme():
    return xfconf_get("xsettings", "/Net/IconThemeName")


def set_icon_theme(name):
    path = find_theme_path(name, DEFAULT_ICON_DIRS + custom_folders("icon_theme_folders"), "index.theme")
    if path:
        ensure_searchable(path, DEFAULT_ICON_DIRS, os.path.join(GLib.get_user_data_dir(), "icons"))
    try:
        xfconf_set("xsettings", "/Net/IconThemeName", name)
    except BackendError as e:
        raise BackendError(_("err_icon_apply", detail=str(e))) from e
