import hashlib
import os

from gi.repository import GdkPixbuf, Gio, GLib


# Cache paths shared with Thunar/Tumbler (freedesktop thumbnail spec)
def _thumbnail_cache_files(path):
    uri = Gio.File.new_for_path(path).get_uri()
    digest = hashlib.md5(uri.encode("utf-8")).hexdigest()
    base = os.path.join(GLib.get_user_cache_dir(), "thumbnails")
    return [os.path.join(base, sub, digest + ".png") for sub in ("normal", "large")]


def _fit_pixbuf(pixbuf, size):
    width, height = pixbuf.get_width(), pixbuf.get_height()
    longest = max(width, height)
    if longest <= size:
        return pixbuf
    scale = size / longest
    return pixbuf.scale_simple(
        max(1, round(width * scale)), max(1, round(height * scale)),
        GdkPixbuf.InterpType.BILINEAR,
    )


# Use the cached thumbnail if still valid, otherwise decode the image
def load_thumbnail(path, size):
    try:
        mtime = str(int(os.stat(path).st_mtime))
    except OSError:
        return None
    for cache_file in _thumbnail_cache_files(path):
        if not os.path.isfile(cache_file):
            continue
        try:
            cached = GdkPixbuf.Pixbuf.new_from_file(cache_file)
        except GLib.Error:
            continue
        if cached.get_option("tEXt::Thumb::MTime") == mtime:
            return _fit_pixbuf(cached, size)
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
    except GLib.Error:
        return None
