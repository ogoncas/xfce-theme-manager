import os

from ..i18n import _
from .common import BackendError, run, xfconf_get, xfconf_set


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".tif"}
WALLPAPER_SCAN_LIMIT = 400


def get_wallpaper_properties():
    try:
        out = run(["xfconf-query", "-c", "xfce4-desktop", "-l"]).stdout
    except BackendError:
        return []
    return [line.strip() for line in out.splitlines() if line.strip().endswith("/last-image")]


def get_current_wallpaper():
    props = get_wallpaper_properties()
    if not props:
        return None
    return xfconf_get("xfce4-desktop", props[0])


def set_wallpaper(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise BackendError(_("err_wallpaper_missing_file", path=path))
    props = get_wallpaper_properties()
    if not props:
        raise BackendError(_("err_wallpaper_no_props"))
    for prop in props:
        xfconf_set("xfce4-desktop", prop, path)
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
