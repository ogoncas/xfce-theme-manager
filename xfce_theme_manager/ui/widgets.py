from gi.repository import Gtk

from ..i18n import _


ICON_APPLY = ("object-select-symbolic", "emblem-ok-symbolic", "emblem-default-symbolic", "gtk-apply")
ICON_CURRENT = ("object-select-symbolic", "emblem-ok-symbolic", "emblem-default-symbolic")
ICON_REFRESH = ("view-refresh-symbolic", "view-refresh", "gtk-refresh")
ICON_ADD = ("list-add-symbolic", "list-add", "gtk-add")
ICON_REMOVE = ("list-remove-symbolic", "list-remove", "gtk-remove")
ICON_EDIT = ("document-edit-symbolic", "accessories-text-editor", "gtk-edit")
ICON_DELETE = ("edit-delete-symbolic", "user-trash-symbolic", "edit-delete", "gtk-delete")
ICON_SETTINGS = ("preferences-system-symbolic", "emblem-system-symbolic", "preferences-system")
ICON_OPEN = ("document-open-symbolic", "folder-open-symbolic", "document-open", "gtk-open")


# First icon the current theme has; the last name is the fallback
def pick_icon(*names):
    theme = Gtk.IconTheme.get_default()
    if theme is not None:
        for name in names:
            if theme.has_icon(name):
                return name
    return names[-1]


def show_toast(widget, message):
    top = widget.get_toplevel()
    if hasattr(top, "show_toast"):
        top.show_toast(message)


def show_error_dialog(widget, message, title=None):
    dialog = Gtk.MessageDialog(
        transient_for=widget.get_toplevel(),
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title or _("error_title"),
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def confirm_dialog(widget, title, message, accept_label):
    dialog = Gtk.MessageDialog(
        transient_for=widget.get_toplevel(),
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.add_button(_("cancel"), Gtk.ResponseType.CANCEL)
    dialog.add_button(accept_label, Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.CANCEL)
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.OK


def make_icon_button(icon_names, label_text, suggested=False):
    if isinstance(icon_names, str):
        icon_names = (icon_names,)
    btn = Gtk.Button(label=label_text)
    btn.set_image(Gtk.Image.new_from_icon_name(pick_icon(*icon_names), Gtk.IconSize.BUTTON))
    btn.set_always_show_image(True)
    if suggested:
        btn.get_style_context().add_class("suggested-action")
    return btn


def make_icon_only_button(icon_names, tooltip):
    btn = Gtk.Button.new_from_icon_name(pick_icon(*icon_names), Gtk.IconSize.BUTTON)
    btn.set_tooltip_text(tooltip)
    return btn
