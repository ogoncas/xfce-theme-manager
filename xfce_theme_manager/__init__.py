import gi

# Pin GTK versions before any gi.repository import (all submodules load this file first)
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
