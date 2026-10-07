from gi.repository import Gtk

from ..backend import FONT_TARGETS
from ..i18n import _
from .widgets import ICON_APPLY, ICON_REFRESH, make_icon_button, show_error_dialog, show_toast


# Shown when a font is not set yet
FALLBACK_FONT = {"monospace": "Monospace 10", "terminal": "Monospace 10"}


class FontsTab(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_border_width(12)

        info_label = Gtk.Label(label=_("fonts_info"), xalign=0)
        info_label.set_line_wrap(True)
        self.pack_start(info_label, False, False, 0)

        grid = Gtk.Grid(row_spacing=10, column_spacing=12)
        self.pack_start(grid, False, False, 6)

        self.rows = {}
        for index, (key, getter, setter) in enumerate(FONT_TARGETS):
            button = Gtk.FontButton()
            button.set_title(_("choose_font"))
            button.set_use_font(True)
            button.set_use_size(False)
            button.set_hexpand(True)
            button.connect("font-set", self._on_font_set, key)
            grid.attach(Gtk.Label(label=_("font_" + key), xalign=0), 0, index, 1, 1)
            grid.attach(button, 1, index, 1, 1)
            self.rows[key] = {
                "button": button, "get": getter, "set": setter, "current": None, "dirty": False,
            }

        spacer = Gtk.Box()
        self.pack_start(spacer, True, True, 0)

        btn_box = Gtk.Box(spacing=8)
        refresh_btn = make_icon_button(ICON_REFRESH, _("refresh"))
        refresh_btn.connect("clicked", lambda w: self.reload())
        apply_btn = make_icon_button(ICON_APPLY, _("apply_fonts"), suggested=True)
        apply_btn.connect("clicked", self.on_apply)
        btn_box.pack_start(refresh_btn, False, False, 0)
        btn_box.pack_end(apply_btn, False, False, 0)
        self.pack_start(btn_box, False, False, 0)

        self.reload()

    def _load_row(self, key):
        row = self.rows[key]
        row["current"] = row["get"]()
        row["button"].set_font(row["current"] or FALLBACK_FONT.get(key, "Sans 10"))
        row["dirty"] = False

    def reload(self):
        for key in self.rows:
            self._load_row(key)

    # Re-read fonts changed elsewhere, but keep the ones picked and not applied yet
    def refresh_current(self):
        for key, row in self.rows.items():
            if not row["dirty"] and row["get"]() != row["current"]:
                self._load_row(key)

    def _on_font_set(self, button, key):
        self.rows[key]["dirty"] = True

    def on_apply(self, *args):
        pending = [(key, row) for key, row in self.rows.items() if row["dirty"]]
        if not pending:
            show_toast(self, _("fonts_no_changes"))
            return

        errors = []
        for key, row in pending:
            try:
                row["set"](row["button"].get_font())
            except Exception as exc:
                errors.append(f"{_('font_' + key)} {exc}")
            else:
                row["dirty"] = False
        self.refresh_current()

        if errors:
            show_error_dialog(self, "\n".join(errors), _("error_apply_title"))
        else:
            show_toast(self, _("fonts_applied"))
