import os

from gi.repository import Gio, GLib, Gtk

from ..backend import (
    get_current_gtk_theme,
    get_current_icon_theme,
    get_current_mousepad_theme,
    get_current_rofi_theme,
    get_gtk_themes,
    get_icon_themes,
    get_mousepad_themes,
    get_rofi_themes,
    rofi_theme_matches,
    set_gtk_theme,
    set_icon_theme,
    set_mousepad_theme,
    set_rofi_theme,
)
from ..config import get_full_config, load_config, save_config
from ..constants import APP_ICON_NAMES
from ..i18n import _
from .collections_tab import CollectionsTab
from .settings_window import SettingsWindow
from .theme_list import ThemeList
from .wallpaper_tab import WallpaperTab
from .widgets import ICON_SETTINGS, make_icon_only_button, pick_icon


def _int_or(value, default, minimum=200):
    return value if isinstance(value, int) and value >= minimum else default


class MainWindow(Gtk.ApplicationWindow):
    PAGES = (
        ("collections", "tab_collections"),
        ("gtk", "tab_gtk"),
        ("icons", "tab_icons"),
        ("wallpaper", "tab_wallpaper"),
        ("mousepad", "tab_mousepad"),
        ("rofi", "tab_rofi"),
    )

    def __init__(self, app, size=None):
        super().__init__(application=app)
        self.app = app
        self._holders = {}
        self._built = set()
        self._toast_timeout = 0
        self._destroyed = False

        cfg = load_config()
        if size is None:
            size = (_int_or(cfg.get("window_width"), 760), _int_or(cfg.get("window_height"), 620))
        self.set_default_size(*size)
        self.set_icon_name(pick_icon(*APP_ICON_NAMES))
        self.use_header = cfg.get("titlebar", "header") != "native"

        settings_btn = make_icon_only_button(ICON_SETTINGS, _("settings_tooltip"))
        settings_btn.connect("clicked", self.on_open_settings)

        if self.use_header:
            header = Gtk.HeaderBar()
            header.set_show_close_button(True)
            header.set_title(_("app_title"))
            header.pack_end(settings_btn)
            self.set_titlebar(header)
        else:
            self.set_title(_("app_title"))

        # Actions behind the Ctrl+, and Ctrl+F shortcuts (Ctrl+Q lives in App)
        for name, callback in (("settings", self.on_open_settings), ("find", self.on_find)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda a, p, cb=callback: cb())
            self.add_action(action)

        # Pages are built on demand so the window opens fast
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        for name, title_key in self.PAGES:
            holder = Gtk.Box()
            self._holders[name] = holder
            self.stack.add_titled(holder, name, _(title_key))
        self.stack.connect("notify::visible-child-name", self._on_visible_child)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.CENTER)

        # Toast bar at the top for quick, non-blocking messages
        self.toast_label = Gtk.Label(xalign=0)
        self.toast_label.show()
        toast_bar = Gtk.InfoBar()
        toast_bar.set_message_type(Gtk.MessageType.INFO)
        toast_bar.get_content_area().add(self.toast_label)
        toast_bar.show()
        self.toast_revealer = Gtk.Revealer()
        self.toast_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.toast_revealer.add(toast_bar)
        self.toast_revealer.show()

        top_row = Gtk.Box(spacing=8)
        top_row.pack_start(switcher, True, False, 0)
        if not self.use_header:
            top_row.pack_end(settings_btn, False, False, 0)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_border_width(8)
        body.pack_start(top_row, False, False, 6)
        body.pack_start(self.stack, True, True, 0)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.pack_start(self.toast_revealer, False, False, 0)
        outer.pack_start(body, True, True, 0)
        self.add(outer)

        self._ensure_page("collections")
        GLib.idle_add(self._build_remaining_pages, priority=GLib.PRIORITY_LOW)

        self.connect("notify::is-active", self._on_active_changed)
        self.connect("delete-event", self._on_delete_event)
        self.connect("destroy", self._on_destroy)

    def _build_page(self, name):
        if name == "collections":
            return CollectionsTab()
        if name == "gtk":
            return ThemeList(get_gtk_themes, get_current_gtk_theme, set_gtk_theme,
                             empty_msg_key="empty_gtk")
        if name == "icons":
            return ThemeList(get_icon_themes, get_current_icon_theme, set_icon_theme,
                             empty_msg_key="empty_icons")
        if name == "wallpaper":
            return WallpaperTab(open_settings_cb=self.on_open_settings)
        if name == "mousepad":
            return ThemeList(get_mousepad_themes, get_current_mousepad_theme, set_mousepad_theme,
                             empty_msg_key="empty_mousepad")
        if name == "rofi":
            return ThemeList(get_rofi_themes, get_current_rofi_theme, set_rofi_theme,
                             label_fn=os.path.basename, match_fn=rofi_theme_matches,
                             empty_msg_key="empty_rofi")
        raise KeyError(name)

    def _ensure_page(self, name):
        if not name or name in self._built or name not in self._holders:
            return
        self._built.add(name)
        page = self._build_page(name)
        self._holders[name].pack_start(page, True, True, 0)
        page.show_all()

    # Build one tab per idle cycle so switching tabs is instant
    def _build_remaining_pages(self):
        if self._destroyed:
            return False
        for name, _title in self.PAGES:
            if name not in self._built:
                self._ensure_page(name)
                return True
        return False

    def _on_visible_child(self, stack, pspec):
        self._ensure_page(stack.get_visible_child_name())

    def _current_page(self):
        holder = self.stack.get_visible_child()
        if holder is None:
            return None
        children = holder.get_children()
        return children[0] if children else None

    # On focus return, refresh the current theme (it may have changed in another app)
    def _on_active_changed(self, *args):
        if self.is_active():
            page = self._current_page()
            if page is not None and hasattr(page, "refresh_current"):
                page.refresh_current()

    def _on_delete_event(self, *args):
        if not self.is_maximized():
            width, height = self.get_size()
            cfg = get_full_config()
            if cfg.get("window_width") != width or cfg.get("window_height") != height:
                cfg["window_width"], cfg["window_height"] = width, height
                try:
                    save_config(cfg)
                except OSError:
                    pass
        return False

    def _on_destroy(self, *args):
        self._destroyed = True
        if self._toast_timeout:
            GLib.source_remove(self._toast_timeout)
            self._toast_timeout = 0

    def show_toast(self, message, timeout_ms=2800):
        self.toast_label.set_text(message)
        self.toast_revealer.set_reveal_child(True)
        if self._toast_timeout:
            GLib.source_remove(self._toast_timeout)
        self._toast_timeout = GLib.timeout_add(timeout_ms, self._hide_toast)

    def _hide_toast(self):
        self._toast_timeout = 0
        self.toast_revealer.set_reveal_child(False)
        return False

    def on_find(self, *args):
        page = self._current_page()
        if page is not None and hasattr(page, "focus_search"):
            page.focus_search()

    def on_open_settings(self, widget=None):
        dialog = SettingsWindow(self, self.app)
        dialog.run_and_apply()
