# XFCE Theme Manager

A small GTK 3 app to change your XFCE look from one window.

- GTK themes
- XFWM (window decoration) themes, in their own tab
- Icon themes
- Fonts: interface, window title, monospace and terminal
- Wallpapers
- Rofi themes
- Mousepad color schemes
- Collections: save and re-apply a full combination of themes, icons, wallpaper, Rofi and Mousepad
- Extra theme and wallpaper folders
- English and Portuguese (follows the system language)

## Install

Debian, Ubuntu, Xubuntu, Mint:

```
sudo apt install ./xfce-theme-manager_2.1_all.deb
```

Download the `.deb` from the [Releases](https://github.com/ogoncas/xfce-themes/releases) page, then launch **XFCE Theme Manager** from the menu, from Settings Manager (Personal section) or run `xfce-theme-manager`.

## Run from source

Requires `python3`, `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-gdkpixbuf-2.0` and `xfconf`.

```
git clone https://github.com/ogoncas/xfce-themes
cd xfce-themes
python3 app.py
```

## Build the .deb

```
./packaging/build-deb.sh
```

The package is written to `dist/`.

## Contributing

See [docs/STRUCTURE.md](docs/STRUCTURE.md) for a map of the code.

## License

[MIT](LICENSE)
