import os

from gi.repository import GLib, Gtk

from ..backend import (
    FONT_TARGETS,
    apply_collection,
    collection_xfwm,
    get_current_cursor_theme,
    get_current_fonts,
    get_current_gtk_theme,
    get_current_icon_theme,
    get_current_mousepad_theme,
    get_current_rofi_theme,
    get_current_wallpaper,
    get_current_xfwm_theme,
    get_cursor_themes,
    get_gtk_themes,
    get_icon_themes,
    get_mousepad_themes,
    get_rofi_themes,
    get_xfwm_themes,
)
from ..config import load_collections, save_collections
from ..i18n import _
from ..paths import default_wallpaper_dirs
from .widgets import (
    confirm_dialog,
    ICON_ADD,
    ICON_APPLY,
    ICON_DELETE,
    ICON_EDIT,
    ICON_OPEN,
    make_icon_button,
    make_icon_only_button,
    run_async,
    show_error_dialog,
    show_toast,
)


class EditCollectionDialog(Gtk.Dialog):
    def __init__(self, parent, col_name, col_data):
        super().__init__(title=_("edit_collection_title"), transient_for=parent, flags=0)
        self.add_buttons(
            _("cancel"), Gtk.ResponseType.CANCEL,
            _("save"), Gtk.ResponseType.OK,
        )
        self.set_default_size(450, 480)

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_border_width(12)

        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        box.pack_start(grid, True, True, 0)

        self.entry_name = Gtk.Entry(text=col_name)
        self.entry_name.set_hexpand(True)
        self.entry_name.set_activates_default(True)
        grid.attach(Gtk.Label(label=_("label_name"), xalign=0), 0, 0, 1, 1)
        grid.attach(self.entry_name, 1, 0, 1, 1)

        self.combo_gtk = self._make_combo(get_gtk_themes(), col_data.get("gtk"))
        grid.attach(Gtk.Label(label=_("label_gtk"), xalign=0), 0, 1, 1, 1)
        grid.attach(self.combo_gtk, 1, 1, 1, 1)

        self.combo_xfwm = self._make_combo(get_xfwm_themes(), collection_xfwm(col_data))
        grid.attach(Gtk.Label(label=_("label_xfwm"), xalign=0), 0, 2, 1, 1)
        grid.attach(self.combo_xfwm, 1, 2, 1, 1)

        self.combo_icon = self._make_combo(get_icon_themes(), col_data.get("icon"))
        grid.attach(Gtk.Label(label=_("label_icons"), xalign=0), 0, 3, 1, 1)
        grid.attach(self.combo_icon, 1, 3, 1, 1)

        self.combo_cursor = self._make_combo(get_cursor_themes(), col_data.get("cursor"))
        grid.attach(Gtk.Label(label=_("label_cursor"), xalign=0), 0, 4, 1, 1)
        grid.attach(self.combo_cursor, 1, 4, 1, 1)

        self.entry_wall = Gtk.Entry(text=col_data.get("wallpaper", ""))
        self.entry_wall.set_hexpand(True)
        browse_btn = make_icon_only_button(ICON_OPEN, _("choose_image"))
        browse_btn.connect("clicked", self._on_browse_wallpaper)
        wall_box = Gtk.Box(spacing=6)
        wall_box.pack_start(self.entry_wall, True, True, 0)
        wall_box.pack_start(browse_btn, False, False, 0)
        grid.attach(Gtk.Label(label=_("label_wallpaper"), xalign=0), 0, 5, 1, 1)
        grid.attach(wall_box, 1, 5, 1, 1)

        self.combo_rofi = self._make_combo(
            get_rofi_themes(), col_data.get("rofi"), display_fn=os.path.basename
        )
        grid.attach(Gtk.Label(label=_("label_rofi"), xalign=0), 0, 6, 1, 1)
        grid.attach(self.combo_rofi, 1, 6, 1, 1)

        self.combo_mouse = self._make_combo(get_mousepad_themes(), col_data.get("mousepad"))
        grid.attach(Gtk.Label(label=_("label_mousepad"), xalign=0), 0, 7, 1, 1)
        grid.attach(self.combo_mouse, 1, 7, 1, 1)

        # One check box per font: unchecked means the collection leaves that font alone
        fonts_label = Gtk.Label(xalign=0)
        fonts_label.set_markup("<b>{}</b>".format(GLib.markup_escape_text(_("fonts_included"))))
        fonts_label.set_margin_top(6)
        grid.attach(fonts_label, 0, 8, 2, 1)
        saved_fonts = col_data.get("fonts") if isinstance(col_data.get("fonts"), dict) else {}
        self.font_rows = {}
        for index, (key, _getter, _setter) in enumerate(FONT_TARGETS):
            check = Gtk.CheckButton(label=_("font_" + key))
            button = Gtk.FontButton()
            button.set_title(_("choose_font"))
            button.set_use_size(False)
            button.set_hexpand(True)
            saved = saved_fonts.get(key)
            if saved:
                button.set_font(saved)
            check.set_active(bool(saved))
            button.set_sensitive(bool(saved))
            check.connect("toggled", lambda c, b=button: b.set_sensitive(c.get_active()))
            grid.attach(check, 0, 9 + index, 1, 1)
            grid.attach(button, 1, 9 + index, 1, 1)
            self.font_rows[key] = (check, button)

        self.set_default_response(Gtk.ResponseType.OK)
        self.show_all()

    # Keeps saved values that are no longer installed so editing does not drop them
    @staticmethod
    def _make_combo(options, active_value, display_fn=None):
        display_fn = display_fn or (lambda v: v)
        options = list(options)
        if active_value and active_value not in options:
            options.append(active_value)
        combo = Gtk.ComboBoxText()
        # Empty first entry means 'not set'
        combo.append(None, "")
        for opt in options:
            combo.append(opt, display_fn(opt))
        if active_value:
            combo.set_active_id(active_value)
        else:
            combo.set_active(0)
        return combo

    def _on_browse_wallpaper(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("choose_image"), transient_for=self, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            _("cancel"), Gtk.ResponseType.CANCEL,
            _("select"), Gtk.ResponseType.OK,
        )
        file_filter = Gtk.FileFilter()
        file_filter.set_name(_("choose_image"))
        file_filter.add_pixbuf_formats()
        dialog.add_filter(file_filter)
        current = self.entry_wall.get_text().strip()
        if current and os.path.isfile(current):
            dialog.set_filename(current)
        else:
            wallpaper_dirs = default_wallpaper_dirs()
            if wallpaper_dirs:
                dialog.set_current_folder(wallpaper_dirs[-1])
        response = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and path:
            self.entry_wall.set_text(path)

    def get_result(self):
        data = {
            "gtk": self.combo_gtk.get_active_id(),
            "icon": self.combo_icon.get_active_id(),
            "cursor": self.combo_cursor.get_active_id(),
            "wallpaper": self.entry_wall.get_text().strip(),
            "rofi": self.combo_rofi.get_active_id(),
            "mousepad": self.combo_mouse.get_active_id(),
        }
        result = {k: v for k, v in data.items() if v}
        # Always stored, so an empty value means "leave the XFWM theme alone"
        result["xfwm"] = self.combo_xfwm.get_active_id() or ""
        fonts = {key: button.get_font() for key, (check, button) in self.font_rows.items()
                 if check.get_active()}
        if fonts:
            result["fonts"] = fonts
        return self.entry_name.get_text().strip(), result


class CollectionsTab(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(12)

        self.collections = load_collections()
        self._applying = False

        info_label = Gtk.Label(label=_("collections_info"), xalign=0)
        info_label.set_line_wrap(True)
        self.pack_start(info_label, False, False, 0)

        form_box = Gtk.Box(spacing=8)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text(_("collection_name_placeholder"))
        self.name_entry.set_hexpand(True)
        self.name_entry.connect("activate", self.on_save_collection)

        save_btn = make_icon_button(ICON_ADD, _("save_current"), suggested=True)
        save_btn.connect("clicked", self.on_save_collection)

        form_box.pack_start(self.name_entry, True, True, 0)
        form_box.pack_start(save_btn, False, False, 0)
        self.pack_start(form_box, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_shadow_type(Gtk.ShadowType.IN)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(False)
        self.listbox.connect("row-activated", lambda lb, row: self.on_apply_collection(None))
        scroller.add(self.listbox)
        self.pack_start(scroller, True, True, 0)

        btn_box = Gtk.Box(spacing=8)

        self.apply_btn = make_icon_button(ICON_APPLY, _("collection_apply"), suggested=True)
        self.apply_btn.connect("clicked", self.on_apply_collection)

        edit_btn = make_icon_button(ICON_EDIT, _("collection_edit"))
        edit_btn.connect("clicked", self.on_edit_collection)

        delete_btn = make_icon_button(ICON_DELETE, _("collection_delete"))
        delete_btn.connect("clicked", self.on_delete_collection)

        btn_box.pack_start(self.apply_btn, False, False, 0)
        btn_box.pack_start(edit_btn, False, False, 0)
        btn_box.pack_end(delete_btn, False, False, 0)
        self.pack_start(btn_box, False, False, 0)

        self.reload_list()

    def focus_search(self):
        self.name_entry.grab_focus()

    def _save(self):
        try:
            save_collections(self.collections)
        except OSError as exc:
            show_error_dialog(self, _("err_config_save", detail=str(exc)), _("error_title"))
            return False
        return True

    def reload_list(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        self.collections = load_collections()
        if not self.collections:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=_("no_collections"), xalign=0)
            lbl.set_margin_top(8)
            lbl.set_margin_bottom(8)
            lbl.set_margin_start(8)
            row.add(lbl)
            row.set_selectable(False)
            row.set_activatable(False)
            self.listbox.add(row)
        else:
            esc = GLib.markup_escape_text
            na = "N/A"

            def base(value):
                return os.path.basename(value) if value else na

            # Up to two font names, then how many more are set
            def fonts_text(data):
                fonts = data.get("fonts")
                names = list(dict.fromkeys(v for v in fonts.values() if v)) if isinstance(fonts, dict) else []
                if not names:
                    return na
                extra = " +{}".format(len(names) - 2) if len(names) > 2 else ""
                return ", ".join(names[:2]) + extra

            for name, data in sorted(self.collections.items(), key=lambda kv: kv[0].lower()):
                row = Gtk.ListBoxRow()
                row.col_name = name

                details = (
                    f"<b>{esc(name)}</b>\n"
                    f" • {esc(_('label_gtk'))} {esc(data.get('gtk') or na)}"
                    f" | {esc(_('label_xfwm'))} {esc(collection_xfwm(data) or na)}\n"
                    f" • {esc(_('label_icons'))} {esc(data.get('icon') or na)}"
                    f" | {esc(_('label_cursor'))} {esc(data.get('cursor') or na)}\n"
                    f" • {esc(_('label_wallpaper'))} {esc(base(data.get('wallpaper')))}"
                    f" | {esc(_('label_fonts'))} {esc(fonts_text(data))}\n"
                    f" • {esc(_('label_rofi'))} {esc(base(data.get('rofi')))}"
                    f" | {esc(_('label_mousepad'))} {esc(data.get('mousepad') or na)}"
                )
                lbl = Gtk.Label(xalign=0)
                lbl.set_markup(details)

                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                box.set_border_width(8)
                box.pack_start(lbl, False, False, 0)
                row.add(box)

                self.listbox.add(row)
        self.listbox.show_all()

    def _selected_name(self):
        row = self.listbox.get_selected_row()
        if row is None or not hasattr(row, "col_name"):
            return None
        return row.col_name

    def on_save_collection(self, widget):
        name = self.name_entry.get_text().strip()
        if not name:
            show_error_dialog(self, _("collection_name_required"), _("warning_title"))
            return

        if name in self.collections and not confirm_dialog(
            self, _("confirm_overwrite_title"),
            _("confirm_overwrite_msg", name=name), _("confirm_overwrite_btn"),
        ):
            return

        current_data = {
            "gtk": get_current_gtk_theme(),
            "icon": get_current_icon_theme(),
            "cursor": get_current_cursor_theme(),
            "wallpaper": get_current_wallpaper(),
            "rofi": get_current_rofi_theme(),
            "mousepad": get_current_mousepad_theme(),
        }
        current_data = {k: v for k, v in current_data.items() if v}
        current_data["xfwm"] = get_current_xfwm_theme() or ""
        fonts = get_current_fonts()
        if fonts:
            current_data["fonts"] = fonts

        self.collections[name] = current_data
        if not self._save():
            return
        self.name_entry.set_text("")
        self.reload_list()
        show_toast(self, _("collection_saved", name=name))

    def on_apply_collection(self, widget):
        name = self._selected_name()
        col_data = self.collections.get(name) if name else None
        if not col_data:
            return
        if self._applying:
            return
        self._applying = True
        self.apply_btn.set_sensitive(False)
        show_toast(self, _("applying"))

        def done(result, error):
            self._applying = False
            self.apply_btn.set_sensitive(True)
            if error is not None:
                show_error_dialog(self, str(error), _("warning_title"))
            else:
                show_toast(self, _("collection_applied", name=name))
            # Other tabs show the new current values right away
            top = self.get_toplevel()
            if hasattr(top, "refresh_pages"):
                top.refresh_pages()

        run_async(self, lambda: apply_collection(col_data), done)

    def on_edit_collection(self, widget):
        col_name = self._selected_name()
        if col_name is None:
            return
        col_data = self.collections.get(col_name, {})

        dialog = EditCollectionDialog(self.get_toplevel(), col_name, col_data)
        response = dialog.run()
        accepted = response == Gtk.ResponseType.OK
        new_name, new_data = dialog.get_result() if accepted else (None, None)
        dialog.destroy()

        if not accepted:
            return
        if not new_name:
            show_error_dialog(self, _("collection_name_required"), _("warning_title"))
            return
        if new_name != col_name and new_name in self.collections and not confirm_dialog(
            self, _("confirm_overwrite_title"),
            _("confirm_overwrite_msg", name=new_name), _("confirm_overwrite_btn"),
        ):
            return

        if new_name != col_name:
            self.collections.pop(col_name, None)
        self.collections[new_name] = new_data
        self._save()
        self.reload_list()

    def on_delete_collection(self, widget):
        name = self._selected_name()
        if name is None or name not in self.collections:
            return
        if not confirm_dialog(
            self, _("confirm_delete_title"),
            _("confirm_delete_msg", name=name), _("collection_delete"),
        ):
            return
        del self.collections[name]
        self._save()
        self.reload_list()
