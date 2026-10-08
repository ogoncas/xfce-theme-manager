import os

from gi.repository import GLib


def dedupe(seq):
    seen = set()
    out = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def xdg_data_dirs():
    return dedupe([GLib.get_user_data_dir(), *GLib.get_system_data_dirs()])


def data_subdirs(subpath, *legacy_dirs):
    dirs = [os.path.expanduser(d) for d in legacy_dirs]
    dirs += [os.path.join(base, subpath) for base in xdg_data_dirs()]
    return dedupe(dirs)


# Computed on demand so a folder created while the app runs is picked up
def default_wallpaper_dirs():
    candidates = data_subdirs("backgrounds")
    home = os.path.expanduser("~")
    # Honor xdg-user-dirs (e.g. ~/Imagens on Portuguese systems)
    pictures = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
    if not pictures or os.path.normpath(pictures) == os.path.normpath(home):
        pictures = os.path.join(home, "Pictures")
    candidates.append(pictures)
    return [d for d in dedupe(candidates) if os.path.isdir(d)]


DEFAULT_GTK_DIRS = data_subdirs("themes", "~/.themes")
DEFAULT_ICON_DIRS = data_subdirs("icons", "~/.icons")
DEFAULT_ROFI_DIRS = dedupe(
    [os.path.join(GLib.get_user_config_dir(), "rofi", "themes")]
    + data_subdirs("rofi/themes")
)
