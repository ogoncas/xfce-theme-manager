import sys

from gi.repository import Gio, GLib, Gtk

from .constants import APP_ICON_NAMES, APP_ID, APP_NAME, APP_PRGNAME
from .ui.css import load_css
from .ui.main_window import MainWindow
from .ui.widgets import pick_icon


# Single instance (D-Bus); the window is rebuilt to apply language, title bar and folder changes
class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        load_css()
        Gtk.Window.set_default_icon_name(pick_icon(*APP_ICON_NAMES))

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Primary>q"])
        self.set_accels_for_action("win.settings", ["<Primary>comma"])
        self.set_accels_for_action("win.find", ["<Primary>f"])

    def do_activate(self):
        if self.window is None:
            self.new_window()
        else:
            self.window.present()

    def _on_quit(self, *args):
        if self.window is not None:
            # Closing fires delete-event, which saves the window size
            self.window.close()
        else:
            self.quit()

    def new_window(self):
        old_window = self.window
        size = old_window.get_size() if old_window is not None else None

        self.window = MainWindow(self, size=size)
        self.window.show_all()
        self.window.present()

        if old_window is not None:
            old_window.destroy()


def main():
    # The program name is the WM_CLASS: lets the panel match the window to the .desktop file
    GLib.set_prgname(APP_PRGNAME)
    GLib.set_application_name(APP_NAME)
    return App().run(sys.argv)
