from gi.repository import Gdk, GLib, Gtk


# Only app-specific classes; everything else comes from the active GTK theme
CSS = b"""
label.status-current {
    padding: 2px 0 6px 0;
    opacity: 0.85;
}
label.status-selected {
    padding: 0 0 4px 0;
    font-weight: 600;
}
label.current-item {
    font-weight: 700;
}
box.folder-section {
    padding: 6px 2px;
}
"""


def load_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_data(CSS)
    except GLib.Error:
        return
    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
