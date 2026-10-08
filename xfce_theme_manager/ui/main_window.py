import os

from gi.repository import Gio, GLib, Gtk

from ..backend import (
    get_current_cursor_theme,
    get_current_gtk_theme,
    get_current_icon_theme,
    get_current_mousepad_theme,
    get_current_rofi_theme,
    get_current_xfwm_theme,
    get_cursor_themes,
    get_gtk_themes,
    get_icon_themes,
    get_mousepad_themes,
    get_rofi_themes,
    get_xfwm_themes,
    process_running,
    rofi_theme_matches,
    set_cursor_theme,
    set_gtk_theme,
    set_icon_theme,
    set_mousepad_theme,
    set_rofi_theme,
    set_xfwm_theme,
)
from ..config import get_full_config, load_config, save_config
from ..constants import APP_ICON_NAMES
from ..i18n import _
from .collections_tab import CollectionsTab
from .fonts_tab import FontsTab
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
        ("xfwm", "tab_xfwm"),
        ("icons", "tab_icons"),
        ("cursors", "tab_cursors"),
        ("fonts", "tab_fonts"),
        ("wallpaper", "tab_wallpaper"),
        ("mousepad", "tab_mousepad"),
        ("rofi", "tab_rofi"),
    )

    def __init__(self, app, size=None):
        super().__init__(application=app)
        self.app = app
        self._holders = {}
        self._tab_buttons = {}
        self._built = set()
        self._toast_timeout = 0
        self._destroyed = False

        cfg = load_config()
        if size is None:
            size = (_int_or(cfg.get("window_width"), 840), _int_or(cfg.get("window_height"), 620))
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
            self.stack.add_named(holder, name)
        self.stack.connect("notify::visible-child-name", self._on_visible_child)

        switcher = self._build_switcher()
        switcher.set_halign(Gtk.Align.CENTER)
        # Scrolls sideways when the window is too narrow for every tab
        self.tab_scroller = Gtk.ScrolledWindow()
        self.tab_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.tab_scroller.set_shadow_type(Gtk.ShadowType.NONE)
        self.tab_scroller.set_propagate_natural_height(True)
        self.tab_scroller.add(switcher)

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
        top_row.pack_start(self.tab_scroller, True, True, 0)
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

        self._warn_if_no_settings_daemon()

        self.connect("notify::is-active", self._on_active_changed)
        self.connect("delete-event", self._on_delete_event)
        self.connect("destroy", self._on_destroy)

    # Own tab bar instead of Gtk.StackSwitcher, which gives every tab the widest label's width
    def _build_switcher(self):
        box = Gtk.Box()
        box.get_style_context().add_class("linked")
        self._tab_buttons = {}
        group = None
        for name, title_key in self.PAGES:
            button = Gtk.RadioButton.new_with_label_from_widget(group, _(title_key))
            button.set_mode(False)
            button.connect("toggled", self._on_tab_toggled, name)
            box.pack_start(button, False, False, 0)
            self._tab_buttons[name] = button
            group = group or button
        return box

    def _on_tab_toggled(self, button, name):
        if button.get_active():
            self.stack.set_visible_child_name(name)
            GLib.idle_add(self._scroll_tab_into_view, button)

    def _scroll_tab_into_view(self, button):
        alloc = button.get_allocation()
        adj = self.tab_scroller.get_hadjustment()
        page = adj.get_page_size()
        if alloc.x < adj.get_value():
            adj.set_value(alloc.x)
        elif alloc.x + alloc.width > adj.get_value() + page:
            adj.set_value(alloc.x + alloc.width - page)
        return False

    # GTK, icon, cursor and font changes reach apps through xfsettingsd
    def _warn_if_no_settings_daemon(self):
        if getattr(self.app, "settings_warned", False):
            return
        self.app.settings_warned = True
        if not process_running("xfsettingsd"):
            GLib.idle_add(lambda: self.show_toast(_("warn_no_xsettings"), 7000) or False)

    def _build_page(self, name):
        if name == "collections":
            return CollectionsTab()
        if name == "gtk":
            return ThemeList(get_gtk_themes, get_current_gtk_theme, set_gtk_theme,
                             empty_msg_key="empty_gtk")
        if name == "xfwm":
            return ThemeList(get_xfwm_themes, get_current_xfwm_theme, set_xfwm_theme,
                             empty_msg_key="empty_xfwm")
        if name == "fonts":
            return FontsTab()
        if name == "icons":
            return ThemeList(get_icon_themes, get_current_icon_theme, set_icon_theme,
                             empty_msg_key="empty_icons")
        if name == "cursors":
            return ThemeList(get_cursor_themes, get_current_cursor_theme, set_cursor_theme,
                             empty_msg_key="empty_cursors")
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
        name = stack.get_visible_child_name()
        self._ensure_page(name)
        button = self._tab_buttons.get(name)
        if button is not None and not button.get_active():
            button.set_active(True)

    # Re-read the current values in every tab that is already built
    def refresh_pages(self):
        for holder in self._holders.values():
            for page in holder.get_children():
                if hasattr(page, "refresh_current"):
                    page.refresh_current()

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
