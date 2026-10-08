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
│   ├── common.py              BackendError, xfconf over D-Bus (xfconf-query fallback), theme lookup
│   ├── gtk.py  xfwm.py  icons.py  cursors.py  wallpaper.py  rofi.py  mousepad.py
│   ├── fonts.py               interface, title, monospace (xfconf) and terminal (terminalrc) fonts
│   └── collections_apply.py   applies a whole collection
└── ui/                        screens
    ├── css.py  widgets.py     app CSS, icons, dialogs, buttons, run_async()
    ├── theme_list.py          filterable list (GTK, XFWM, icons, cursors, Rofi, Mousepad)
    ├── fonts_tab.py           Fonts tab (one font button per setting)
    ├── collections_tab.py     Collections tab + edit dialog
    ├── wallpaper_tab.py       Wallpaper tab
    ├── settings_window.py     Settings (general, folders, about)
    └── main_window.py         main window
packaging/build-deb.sh         builds the .deb
tests/                         pytest suite (pure logic, locale parity)
```

Where to change things:
- New theme type: add `backend/<type>.py`, then a tab in `ui/main_window.py` (`PAGES` and `_build_page`).
- New language: add a file in `locales/` and register it in `i18n.py`.
- Look and feel: `ui/css.py` and `ui/widgets.py`.
