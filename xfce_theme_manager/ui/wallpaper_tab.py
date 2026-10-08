import os
import threading

from gi.repository import GdkPixbuf, GLib, Gtk

from ..backend import get_current_wallpaper, scan_wallpaper_images, set_wallpaper
from ..config import load_wallpaper_folders
from ..i18n import _
from ..thumbnails import load_preview, load_thumbnail
from .widgets import (
    ICON_APPLY,
    ICON_REFRESH,
    make_icon_button,
    run_async,
    show_error_dialog,
    show_toast,
)


class WallpaperTab(Gtk.Box):
    THUMB_SIZE = 128
    BATCH_SIZE = 8

    def __init__(self, open_settings_cb=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(12)
        self.open_settings_cb = open_settings_cb
        self.selected_path = None

        self._scan_id = 0
        self._truncated = False
        self._current_wallpaper = None
        self._applying = False

        self.preview = Gtk.Image()
        self.preview.set_size_request(-1, 180)
        preview_frame = Gtk.Frame()
        preview_frame.set_shadow_type(Gtk.ShadowType.IN)
        preview_frame.add(self.preview)
        self.pack_start(preview_frame, False, False, 0)

        self.selected_status = Gtk.Label(xalign=0)
        self.selected_status.get_style_context().add_class("status-selected")
        self.pack_start(self.selected_status, False, False, 0)

        hint_row = Gtk.Box(spacing=8)
        hint_label = Gtk.Label(label=_("configure_folders_hint"), xalign=0)
        hint_label.get_style_context().add_class("status-current")
        hint_row.pack_start(hint_label, True, True, 0)
        if self.open_settings_cb:
            open_btn = Gtk.Button.new_with_label(_("open_settings"))
            open_btn.connect("clicked", lambda w: self.open_settings_cb())
            hint_row.pack_start(open_btn, False, False, 0)
        self.pack_start(hint_row, False, False, 0)

        status_box = Gtk.Box(spacing=8)
        self.count_label = Gtk.Label(xalign=0)
        self.spinner = Gtk.Spinner()
        status_box.pack_start(self.count_label, True, True, 0)
        status_box.pack_start(self.spinner, False, False, 0)
        self.pack_start(status_box, False, False, 0)

        grid_scroller = Gtk.ScrolledWindow()
        grid_scroller.set_vexpand(True)
        grid_scroller.set_shadow_type(Gtk.ShadowType.IN)
        self.store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        self.iconview = Gtk.IconView(model=self.store)
        self.iconview.set_pixbuf_column(0)
        self.iconview.set_text_column(2)
        self.iconview.set_tooltip_column(1)
        self.iconview.set_item_width(self.THUMB_SIZE + 12)
        self.iconview.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.iconview.connect("selection-changed", self.on_icon_selected)
        self.iconview.connect("item-activated", lambda iv, path: self.apply_wallpaper())
        grid_scroller.add(self.iconview)
        self.pack_start(grid_scroller, True, True, 0)

        btn_box = Gtk.Box(spacing=8)
        self.rescan_btn = make_icon_button(ICON_REFRESH, _("refresh"))
        self.rescan_btn.connect("clicked", lambda w: self.rescan())

        self.apply_btn = make_icon_button(ICON_APPLY, _("wallpaper_apply_btn"), suggested=True)
        self.apply_btn.connect("clicked", self.on_apply)
        self.apply_btn.set_sensitive(False)

        btn_box.pack_start(self.rescan_btn, False, False, 0)
        btn_box.pack_end(self.apply_btn, False, False, 0)
        self.pack_start(btn_box, False, False, 0)

        self.connect("destroy", self._on_destroy)
        self.update_selected_status()
        self.rescan()

    def _on_destroy(self, *args):
        # Invalidate any scan or idle callback still running
        self._scan_id += 1

    def focus_search(self):
        self.iconview.grab_focus()

    def update_selected_status(self):
        text = os.path.basename(self.selected_path) if self.selected_path else _("none_selected")
        self.selected_status.set_markup(
            "<b>{}</b> {}".format(
                GLib.markup_escape_text(_("selected_label")),
                GLib.markup_escape_text(text),
            )
        )
        self.apply_btn.set_sensitive(bool(self.selected_path))

    # One worker scans the folders and decodes thumbnails; the main loop only receives finished batches
    def rescan(self):
        self._scan_id += 1
        scan_id = self._scan_id
        self.store.clear()
        self.selected_path = None
        self.preview.clear()
        self.update_selected_status()

        folders = load_wallpaper_folders()
        if not folders:
            self.spinner.stop()
            self.spinner.hide()
            self.count_label.set_text(_("no_folder_added"))
            return

        self.count_label.set_text(_("scanning_images"))
        self.spinner.show()
        self.spinner.start()
        self.rescan_btn.set_sensitive(False)

        def worker():
            try:
                images, truncated = scan_wallpaper_images(folders)
                current = get_current_wallpaper()
            except Exception:
                images, truncated, current = [], False, None
            GLib.idle_add(self._on_listed, scan_id, truncated, current)
            loaded = 0
            batch = []
            for path in images:
                if scan_id != self._scan_id:
                    return
                thumb = load_thumbnail(path, self.THUMB_SIZE)
                if thumb is None:
                    continue
                loaded += 1
                batch.append((path, thumb))
                if len(batch) >= self.BATCH_SIZE:
                    GLib.idle_add(self._on_batch, scan_id, batch)
                    batch = []
            if batch:
                GLib.idle_add(self._on_batch, scan_id, batch)
            GLib.idle_add(self._finish_scan, scan_id, loaded)

        threading.Thread(target=worker, daemon=True).start()

    def _on_listed(self, scan_id, truncated, current):
        if scan_id == self._scan_id:
            self._truncated = truncated
            self._current_wallpaper = current
        return False

    def _on_batch(self, scan_id, batch):
        # Ignore results from an outdated scan
        if scan_id != self._scan_id:
            return False
        for path, thumb in batch:
            tree_iter = self.store.append([thumb, path, os.path.basename(path)])
            if self.selected_path is None and path == self._current_wallpaper:
                tree_path = self.store.get_path(tree_iter)
                self.iconview.select_path(tree_path)
                self.iconview.scroll_to_path(tree_path, True, 0.5, 0.5)
        return False

    def _finish_scan(self, scan_id, loaded):
        if scan_id != self._scan_id:
            return False
        self.spinner.stop()
        self.spinner.hide()
        self.rescan_btn.set_sensitive(True)
        if loaded <= 0:
            self.count_label.set_text(_("no_image_found"))
        elif self._truncated:
            self.count_label.set_text(_("images_limit_reached", count=loaded))
        else:
            self.count_label.set_text(_("images_found", count=loaded))
        return False

    def on_icon_selected(self, iconview):
        items = iconview.get_selected_items()
        if not items:
            self.selected_path = None
            self.preview.clear()
            self.update_selected_status()
            return
        tree_iter = self.store.get_iter(items[0])
        path = self.store.get_value(tree_iter, 1)
        self.selected_path = path
        self.update_selected_status()
        self._show_preview(path)

    # Decoding a large image can take a while, so it runs off the main loop
    def _show_preview(self, path):
        def done(pixbuf, error):
            if path != self.selected_path:
                return
            if pixbuf is not None:
                self.preview.set_from_pixbuf(pixbuf)
            else:
                self.preview.clear()

        run_async(self, lambda: load_preview(path, 500, 180), done)

    def on_apply(self, widget):
        self.apply_wallpaper()

    def apply_wallpaper(self):
        if not self.selected_path:
            show_error_dialog(self, _("select_image_prompt"), _("error_apply_wallpaper_title"))
            return
        if self._applying:
            return
        path = self.selected_path
        self._applying = True
        self.apply_btn.set_sensitive(False)

        def done(result, error):
            self._applying = False
            self.apply_btn.set_sensitive(bool(self.selected_path))
            if error is not None:
                show_error_dialog(self, str(error), _("error_apply_wallpaper_title"))
            else:
                show_toast(self, _("wallpaper_applied", name=os.path.basename(path)))

        run_async(self, lambda: set_wallpaper(path), done)
