import copy

from gi.repository import GLib, Gtk

from ..config import get_full_config, save_config
from ..constants import APP_ICON_NAMES, APP_NAME, APP_VERSION, DEVELOPER, GITHUB_URL, LICENSE_NAME
from ..i18n import _, detect_system_language, i18n
from ..paths import DEFAULT_GTK_DIRS, DEFAULT_ICON_DIRS, DEFAULT_ROFI_DIRS, default_wallpaper_dirs
from .widgets import ICON_ADD, ICON_REMOVE, make_icon_only_button, pick_icon, show_error_dialog


# Edits the in-memory list; it is saved only when Settings are applied
class FolderListEditor(Gtk.Box):
    def __init__(self, folders_ref, default_dirs, default_note=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.get_style_context().add_class("folder-section")
        self.folders_ref = folders_ref

        info = Gtk.Label(xalign=0)
        if default_dirs:
            info.set_markup(
                "<small>{}: {}</small>".format(
                    GLib.markup_escape_text(_("default_folders")),
                    GLib.markup_escape_text(", ".join(default_dirs)),
                )
            )
        elif default_note:
            info.set_markup("<small>{}</small>".format(GLib.markup_escape_text(default_note)))
        info.set_line_wrap(True)
        self.pack_start(info, False, False, 0)

        row = Gtk.Box(spacing=8)
        scroller = Gtk.ScrolledWindow()
        scroller.set_size_request(-1, 90)
        scroller.set_shadow_type(Gtk.ShadowType.IN)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scroller.add(self.listbox)
        row.pack_start(scroller, True, True, 0)

        btns = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        add_btn = make_icon_only_button(ICON_ADD, _("add"))
        add_btn.connect("clicked", self.on_add)
        rem_btn = make_icon_only_button(ICON_REMOVE, _("remove"))
        rem_btn.connect("clicked", self.on_remove)
        btns.pack_start(add_btn, False, False, 0)
        btns.pack_start(rem_btn, False, False, 0)
        row.pack_start(btns, False, False, 0)

        self.pack_start(row, False, False, 0)
        self.refresh()

    def refresh(self):
        for c in self.listbox.get_children():
            self.listbox.remove(c)
        if not self.folders_ref:
            r = Gtk.ListBoxRow()
            r.add(Gtk.Label(label=_("no_custom_folders"), xalign=0))
            r.set_selectable(False)
            self.listbox.add(r)
        else:
            for f in self.folders_ref:
                r = Gtk.ListBoxRow()
                r.folder_path = f
                r.add(Gtk.Label(label=f, xalign=0))
                self.listbox.add(r)
        self.listbox.show_all()

    def on_add(self, widget):
        dialog = Gtk.FileChooserDialog(
            title=_("choose_folder"),
            transient_for=self.get_toplevel(),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            _("cancel"), Gtk.ResponseType.CANCEL,
            _("add"), Gtk.ResponseType.OK,
        )
        response = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and path and path not in self.folders_ref:
            self.folders_ref.append(path)
            self.refresh()

    def on_remove(self, widget):
        row = self.listbox.get_selected_row()
        if row is None or not hasattr(row, "folder_path"):
            return
        self.folders_ref.remove(row.folder_path)
        self.refresh()


class SettingsWindow(Gtk.Dialog):
    def __init__(self, parent, app):
        super().__init__(title=_("settings_title"), transient_for=parent, flags=0)
        self.set_modal(True)
        self.set_default_size(700, 520)
        self.app = app

        self._original_config = get_full_config()
        self.pending_config = copy.deepcopy(self._original_config)

        self.add_button(_("cancel"), Gtk.ResponseType.CANCEL)
        apply_btn = self.add_button(_("apply"), Gtk.ResponseType.OK)
        apply_btn.get_style_context().add_class("suggested-action")

        content = self.get_content_area()
        content.set_border_width(0)
        content.set_spacing(0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_vexpand(True)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)

        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(self.stack)
        hbox.pack_start(sidebar, False, False, 0)
        hbox.pack_start(self.stack, True, True, 0)
        content.pack_start(hbox, True, True, 0)

        self.stack.add_titled(self._build_general_page(), "general", _("tab_general"))
        self.stack.add_titled(self._build_folders_page(), "folders", _("tab_folders"))
        self.stack.add_titled(self._build_about_page(), "about", _("tab_about"))

        self.show_all()

    def _build_general_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(18)

        lang_label = Gtk.Label(xalign=0)
        lang_label.set_markup(f"<b>{GLib.markup_escape_text(_('language_label'))}</b>")
        box.pack_start(lang_label, False, False, 0)

        current_lang = self.pending_config.get("language", "auto")

        radio_auto = Gtk.RadioButton.new_with_label_from_widget(None, _("language_auto"))
        radio_pt = Gtk.RadioButton.new_with_label_from_widget(radio_auto, _("language_pt"))
        radio_en = Gtk.RadioButton.new_with_label_from_widget(radio_auto, _("language_en"))

        radios = {"auto": radio_auto, "pt_BR": radio_pt, "en": radio_en}
        radios.get(current_lang, radio_auto).set_active(True)

        for key, radio in radios.items():
            radio.connect("toggled", self._on_language_toggled, key)
            box.pack_start(radio, False, False, 0)

        hint = Gtk.Label(xalign=0)
        hint.set_markup(
            "<small>{}</small>".format(
                GLib.markup_escape_text(_("language_auto_hint", lang=_("language_pt") if detect_system_language() == "pt_BR" else _("language_en")))
            )
        )
        box.pack_start(hint, False, False, 0)

        # Title bar: integrated header bar (CSD) or native xfwm4 decoration
        tb_label = Gtk.Label(xalign=0)
        tb_label.set_markup(f"<b>{GLib.markup_escape_text(_('titlebar_label'))}</b>")
        tb_label.set_margin_top(10)
        box.pack_start(tb_label, False, False, 0)

        radio_header = Gtk.RadioButton.new_with_label_from_widget(None, _("titlebar_header"))
        radio_native = Gtk.RadioButton.new_with_label_from_widget(radio_header, _("titlebar_native"))
        tb_radios = {"header": radio_header, "native": radio_native}
        tb_radios.get(self.pending_config.get("titlebar", "header"), radio_header).set_active(True)
        for key, radio in tb_radios.items():
            radio.connect("toggled", self._on_titlebar_toggled, key)
            box.pack_start(radio, False, False, 0)

        return box

    def _on_language_toggled(self, radio, key):
        if radio.get_active():
            self.pending_config["language"] = key

    def _on_titlebar_toggled(self, radio, key):
        if radio.get_active():
            self.pending_config["titlebar"] = key

    def _build_folders_page(self):
        outer = Gtk.ScrolledWindow()
        outer.set_shadow_type(Gtk.ShadowType.NONE)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(18)

        intro = Gtk.Label(label=_("folders_intro"), xalign=0)
        intro.set_line_wrap(True)
        box.pack_start(intro, False, False, 0)

        categories = [
            ("folders_wallpaper", "wallpaper_folders", default_wallpaper_dirs(), None),
            ("folders_gtk", "gtk_theme_folders", DEFAULT_GTK_DIRS, None),
            ("folders_icons", "icon_theme_folders", DEFAULT_ICON_DIRS, None),
            ("folders_rofi", "rofi_theme_folders", DEFAULT_ROFI_DIRS, None),
            ("folders_mousepad", "mousepad_style_folders", [], _("folders_mousepad_default_note")),
        ]

        for title_key, config_key, default_dirs, note in categories:
            expander = Gtk.Expander(label=_(title_key))
            expander.set_expanded(False)
            editor = FolderListEditor(self.pending_config[config_key], default_dirs, note)
            expander.add(editor)
            box.pack_start(expander, False, False, 0)

        outer.add(box)
        return outer

    def _build_about_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(24)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name(pick_icon(*APP_ICON_NAMES), Gtk.IconSize.DIALOG)
        icon.set_pixel_size(64)
        box.pack_start(icon, False, False, 4)

        title = Gtk.Label()
        title.set_markup(f"<span size='x-large' weight='bold'>{GLib.markup_escape_text(APP_NAME)}</span>")
        box.pack_start(title, False, False, 0)

        version = Gtk.Label(label=_("version_label", version=APP_VERSION))
        box.pack_start(version, False, False, 0)

        desc = Gtk.Label(label=_("about_description"))
        desc.set_line_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_max_width_chars(48)
        box.pack_start(desc, False, False, 8)

        dev = Gtk.Label()
        dev.set_markup(
            "<b>{}</b> {}".format(
                GLib.markup_escape_text(_("developer_label") + ":"),
                GLib.markup_escape_text(DEVELOPER),
            )
        )
        box.pack_start(dev, False, False, 0)

        lic = Gtk.Label()
        lic.set_markup(
            "<b>{}</b> {}".format(
                GLib.markup_escape_text(_("license_label") + ":"),
                GLib.markup_escape_text(LICENSE_NAME),
            )
        )
        box.pack_start(lic, False, False, 0)

        link = Gtk.LinkButton.new_with_label(GITHUB_URL, _("view_on_github"))
        link.set_halign(Gtk.Align.CENTER)
        box.pack_start(link, False, False, 8)

        return box

    def run_and_apply(self):
        response = self.run()
        applied = False
        if response == Gtk.ResponseType.OK:
            changed = self.pending_config != self._original_config
            if changed:
                try:
                    save_config(self.pending_config)
                except OSError as exc:
                    changed = False
                    show_error_dialog(self.get_transient_for(), _("err_config_save", detail=str(exc)))
                else:
                    i18n.apply_language(self.pending_config.get("language", "auto"))
            applied = changed
        self.destroy()
        if applied:
            # Language, title bar and folders require rebuilding the main window
            self.app.new_window()
        return applied
