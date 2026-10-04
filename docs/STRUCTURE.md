# Code structure

```
app.py                         entry point (only calls main())
xfce_theme_manager/
├── __init__.py                pins GTK versions (must run before any gi import)
├── application.py             Gtk.Application (single instance) + main()
├── constants.py               name, version, ID, author, license, URL
├── i18n.py                    language detection and the `_` translate function
├── locales/en.py, pt_br.py    translations
├── paths.py                   XDG and default theme/wallpaper folders
├── config.py                  config.json (cache, normalization, collections)
├── fileio.py                  atomic file writes
├── thumbnails.py              thumbnails (shared Thunar/Tumbler cache)
├── backend/                   no UI: reads and applies system settings
│   ├── common.py              BackendError, run(), xfconf helpers, theme lookup
│   ├── gtk.py  icons.py  wallpaper.py  rofi.py  mousepad.py
│   └── collections_apply.py   applies a whole collection
└── ui/                        screens
    ├── css.py  widgets.py     app CSS, icons, dialogs, buttons
    ├── theme_list.py          filterable list (GTK, icons, Rofi, Mousepad)
    ├── collections_tab.py     Collections tab + edit dialog
    ├── wallpaper_tab.py       Wallpaper tab
    ├── settings_window.py     Settings (general, folders, about)
    └── main_window.py         main window
packaging/build-deb.sh         builds the .deb
```

Where to change things:
- New theme type: add `backend/<type>.py`, then a tab in `ui/main_window.py` (`PAGES` and `_build_page`).
- New language: add a file in `locales/` and register it in `i18n.py`.
- Look and feel: `ui/css.py` and `ui/widgets.py`.
