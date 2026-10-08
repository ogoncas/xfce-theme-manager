from gi.repository import GLib, Gtk, Pango

from ..i18n import _
from .widgets import (
    ICON_APPLY,
    ICON_CURRENT,
    ICON_REFRESH,
    make_icon_button,
    pick_icon,
    show_error_dialog,
    show_toast,
)


# Rows are built once per reload; the filter only hides them
class ThemeList(Gtk.Box):
    def __init__(self, get_items, get_current, apply_fn, label_fn=None,
                 empty_msg_key="", match_fn=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(12)

        self.get_items = get_items
        self.get_current = get_current
        self.apply_fn = apply_fn
        self.label_fn = label_fn or (lambda x: x)
        self.match_fn = match_fn or self._default_match
        self.empty_msg_key = empty_msg_key
        self.all_items = []
        self.current = None
        self._query = ""

        self.status = Gtk.Label(xalign=0)
        self.status.get_style_context().add_class("status-current")
        self.pack_start(self.status, False, False, 0)

        self.selected_status = Gtk.Label(xalign=0)
        self.selected_status.get_style_context().add_class("status-selected")
        self.pack_start(self.selected_status, False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("filter_placeholder"))
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.pack_start(self.search_entry, False, False, 0)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_vexpand(True)
        self.scroller.set_shadow_type(Gtk.ShadowType.IN)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(False)
        self.listbox.set_filter_func(self._filter_row, None)
        self.placeholder = Gtk.Label(xalign=0.5)
        self.placeholder.set_margin_top(14)
        self.placeholder.set_margin_bottom(14)
        self.placeholder.show()
        self.listbox.set_placeholder(self.placeholder)
        self._sel_handler = self.listbox.connect("row-selected", self.on_row_selected)
        self.listbox.connect("row-activated", self.on_row_activated)
        self.scroller.add(self.listbox)
        self.pack_start(self.scroller, True, True, 0)

        btn_box = Gtk.Box(spacing=8)

        refresh_btn = make_icon_button(ICON_REFRESH, _("refresh"))
        refresh_btn.connect("clicked", lambda w: self.reload())

        self.apply_btn = make_icon_button(ICON_APPLY, _("apply_theme"), suggested=True)
        self.apply_btn.connect("clicked", self.on_apply)
        self.apply_btn.set_sensitive(False)

        btn_box.pack_start(refresh_btn, False, False, 0)
        btn_box.pack_end(self.apply_btn, False, False, 0)
        self.pack_start(btn_box, False, False, 0)

        self._scrolled_once = False
        self.connect("map", self._on_map)
        self.reload()

    def _default_match(self, item, current):
        return bool(current) and (item == current or self.label_fn(item) == current)

    def reload(self):
        self.all_items = list(self.get_items())
        self.current = self.get_current()
        self._rebuild()

    # Re-read only the current theme (it may change outside the app)
    def refresh_current(self):
        new_current = self.get_current()
        if new_current != self.current:
            self.current = new_current
            self._update_status()
            self._mark_current()

    def _make_row(self, item):
        row = Gtk.ListBoxRow()
        row.item_value = item
        row.label_text = self.label_fn(item)

        box = Gtk.Box(spacing=8)
        box.set_border_width(4)
        row.lbl = Gtk.Label(label=row.label_text, xalign=0)
        row.lbl.set_hexpand(True)
        row.lbl.set_ellipsize(Pango.EllipsizeMode.END)
        row.mark = Gtk.Image.new_from_icon_name(pick_icon(*ICON_CURRENT), Gtk.IconSize.MENU)
        row.mark.set_no_show_all(True)
        row.mark.set_tooltip_text(_("current_theme").rstrip(":"))
        box.pack_start(row.lbl, True, True, 0)
        box.pack_end(row.mark, False, False, 0)
        row.add(box)
        self._style_row(row, self.match_fn(item, self.current))
        return row

    @staticmethod
    def _style_row(row, is_current):
        row.is_current = is_current
        ctx = row.lbl.get_style_context()
        if is_current:
            ctx.add_class("current-item")
        else:
            ctx.remove_class("current-item")
        row.mark.set_visible(is_current)

    def _mark_current(self):
        for row in self.listbox.get_children():
            if hasattr(row, "item_value"):
                self._style_row(row, self.match_fn(row.item_value, self.current))

    def _rebuild(self):
        keep = self.selected_value()
        # Block the selection signal while rows are rebuilt
        self.listbox.handler_block(self._sel_handler)
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        to_select = current_row = None
        for item in self.all_items:
            row = self._make_row(item)
            self.listbox.add(row)
            if keep is not None and item == keep:
                to_select = row
            if row.is_current and current_row is None:
                current_row = row
        # Keep the selection; fall back to the current theme if the item is gone
        to_select = to_select or current_row

        if not self.all_items and self.empty_msg_key:
            self.placeholder.set_text(_(self.empty_msg_key))
        else:
            self.placeholder.set_text(_("empty_generic"))

        self.listbox.show_all()
        for row in self.listbox.get_children():
            row.mark.set_visible(row.is_current)
        if to_select is not None:
            self.listbox.select_row(to_select)
        self.listbox.handler_unblock(self._sel_handler)

        self._update_status()
        self.update_selected_status()
        self._scrolled_once = False
        if self.get_mapped():
            GLib.idle_add(self._scroll_to_selected)

    def _update_status(self):
        self.status.set_markup(
            "<b>{}</b> {}".format(
                GLib.markup_escape_text(_("current_theme")),
                GLib.markup_escape_text(self.current or _("not_available")),
            )
        )

    def selected_value(self):
        row = self.listbox.get_selected_row()
        if row is not None and hasattr(row, "item_value"):
            return row.item_value
        return None

    def update_selected_status(self):
        value = self.selected_value()
        text = self.label_fn(value) if value is not None else _("none_selected")
        self.selected_status.set_markup(
            "<b>{}</b> {}".format(
                GLib.markup_escape_text(_("selected_label")),
                GLib.markup_escape_text(text),
            )
        )
        self.apply_btn.set_sensitive(value is not None)

    def _on_map(self, *args):
        if not self._scrolled_once:
            GLib.idle_add(self._scroll_to_selected)

    def _scroll_to_selected(self):
        row = self.listbox.get_selected_row()
        if row is None or not row.get_mapped() or row.get_allocated_height() <= 1:
            return False
        coords = row.translate_coordinates(self.listbox, 0, 0)
        if coords is None:
            return False
        adj = self.scroller.get_vadjustment()
        target = coords[1] - (adj.get_page_size() - row.get_allocated_height()) / 2
        adj.set_value(max(0, min(target, adj.get_upper() - adj.get_page_size())))
        self._scrolled_once = True
        return False

    def _filter_row(self, row, *args):
        if not self._query:
            return True
        return self._query in getattr(row, "label_text", "").lower()

    def on_search_changed(self, entry):
        self._query = entry.get_text().strip().lower()
        self.listbox.invalidate_filter()
        # Never leave a hidden row selected: Apply would act on an item the user cannot see
        row = self.listbox.get_selected_row()
        if row is not None and not self._filter_row(row):
            self.listbox.unselect_all()

    def focus_search(self):
        self.search_entry.grab_focus()

    def on_row_selected(self, listbox, row):
        self.update_selected_status()

    def on_row_activated(self, listbox, row):
        self.on_apply()

    def on_apply(self, *args):
        value = self.selected_value()
        if value is None:
            show_error_dialog(self, _("select_item_first"), _("error_apply_title"))
            return
        try:
            self.apply_fn(value)
        except Exception as exc:
            show_error_dialog(self, str(exc), _("error_apply_title"))
        else:
            show_toast(self, _("applied_ok", name=self.label_fn(value)))
        self.current = self.get_current()
        self._update_status()
        self._mark_current()
