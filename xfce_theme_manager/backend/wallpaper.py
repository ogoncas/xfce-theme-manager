import os

from ..i18n import _
from .common import BackendError, run, xfconf_get, xfconf_list, xfconf_set


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".tif"}
WALLPAPER_SCAN_LIMIT = 400
DESKTOP_CHANNEL = "xfce4-desktop"
IMAGE_STYLE_NONE = "0"
IMAGE_STYLE_ZOOMED = "5"


# Sorted so the first one is stable: workspace 0 before the others
def _wallpaper_values():
    values = {k: v for k, v in xfconf_list(DESKTOP_CHANNEL).items() if k.endswith("/last-image")}
    return sorted(values.items(), key=lambda kv: ("/workspace0/" not in kv[0], kv[0]))


def get_wallpaper_properties():
    return [prop for prop, _value in _wallpaper_values()]


def get_current_wallpaper():
    for _prop, value in _wallpaper_values():
        if value:
            return value
    return None


def set_wallpaper(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise BackendError(_("err_wallpaper_missing_file", path=path))
    props = get_wallpaper_properties()
    if not props:
        raise BackendError(_("err_wallpaper_no_props"))
    for prop in props:
        xfconf_set(DESKTOP_CHANNEL, prop, path)
        # Style "none" would hide the image that was just chosen
        style_prop = prop.rsplit("/", 1)[0] + "/image-style"
        if xfconf_get(DESKTOP_CHANNEL, style_prop) == IMAGE_STYLE_NONE:
            xfconf_set(DESKTOP_CHANNEL, style_prop, IMAGE_STYLE_ZOOMED, "int")
    try:
        # xfdesktop already watches xfconf; the reload is only a backup and must not fail
        run(["xfdesktop", "--reload"], check=False, timeout=5)
    except BackendError:
        pass


def scan_wallpaper_images(folders, limit=WALLPAPER_SCAN_LIMIT):
    """Return (paths, truncated); truncated is True if the limit was hit."""
    results = []
    seen = set()
    for folder in folders:
        folder = os.path.expanduser(folder)
        if not os.path.isdir(folder):
            continue
        for root, dirs, files in os.walk(folder):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for fname in sorted(files):
                if fname.startswith("."):
                    continue
                if os.path.splitext(fname)[1].lower() not in IMAGE_EXTENSIONS:
                    continue
                full = os.path.join(root, fname)
                real = os.path.realpath(full)
                if real in seen:
                    continue
                seen.add(real)
                if len(results) >= limit:
                    return results, True
                results.append(full)
    return results, False
