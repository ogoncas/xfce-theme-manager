import copy
import json
import os

from gi.repository import GLib

from .fileio import atomic_write_text
from .paths import dedupe, default_wallpaper_dirs


CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "xfce-theme-manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


FOLDER_KEYS = (
    "wallpaper_folders",
    "gtk_theme_folders",
    "icon_theme_folders",
    "rofi_theme_folders",
    "mousepad_style_folders",
)


# In-memory cache of config.json, invalidated by the file's mtime
_config_cache = {"mtime": None, "data": None}


def _config_mtime():
    try:
        return os.stat(CONFIG_FILE).st_mtime_ns
    except OSError:
        return None


def load_config():
    """Return the shared config dict (callers must not modify it)."""
    mtime = _config_mtime()
    if _config_cache["data"] is None or _config_cache["mtime"] != mtime:
        data = {}
        if mtime is not None:
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except (OSError, ValueError):
                data = {}
        _config_cache["mtime"] = mtime
        _config_cache["data"] = data
    return _config_cache["data"]


def save_config(cfg):
    atomic_write_text(CONFIG_FILE, json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    _config_cache["mtime"] = _config_mtime()
    _config_cache["data"] = copy.deepcopy(cfg)


def _normalize_config(cfg):
    """Fix missing or invalid keys in place. Return True if anything changed."""
    changed = False
    if not isinstance(cfg.get("language"), str):
        cfg["language"] = "auto"
        changed = True
    if cfg.get("titlebar") not in ("header", "native"):
        cfg["titlebar"] = "header"
        changed = True
    for key in FOLDER_KEYS:
        value = cfg.get(key)
        if not isinstance(value, list):
            cfg[key] = []
            changed = True
        else:
            clean = [p for p in value if isinstance(p, str) and p]
            if clean != value:
                cfg[key] = clean
                changed = True
    if not isinstance(cfg.get("collections"), dict):
        cfg["collections"] = {}
        changed = True
    return changed


def get_full_config():
    """Return an independent copy of the config with all keys present."""
    cfg = copy.deepcopy(load_config())
    if _normalize_config(cfg):
        try:
            save_config(cfg)
        except OSError:
            pass
    return cfg


def custom_folders(key):
    value = load_config().get(key)
    if not isinstance(value, list):
        return []
    return [os.path.expanduser(p) for p in value if isinstance(p, str) and p]


def load_wallpaper_folders():
    return dedupe(default_wallpaper_dirs() + custom_folders("wallpaper_folders"))


def load_collections():
    value = load_config().get("collections")
    return copy.deepcopy(value) if isinstance(value, dict) else {}


def save_collections(collections):
    cfg = get_full_config()
    cfg["collections"] = collections
    save_config(cfg)
