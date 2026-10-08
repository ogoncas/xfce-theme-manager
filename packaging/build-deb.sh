#!/bin/sh
# Builds xfce-theme-manager_<version>_all.deb from this source tree.
# Usage: ./packaging/build-deb.sh   (run from anywhere; needs dpkg-deb)
set -eu

SRC="$(cd "$(dirname "$0")/.." && pwd)"
PKG=xfce-theme-manager
CONSTANTS="$SRC/xfce_theme_manager/constants.py"
VERSION="$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' "$CONSTANTS")"
APP_ID="$(sed -n 's/^APP_ID = "\(.*\)"/\1/p' "$CONSTANTS")"
CHANGELOG_ENTRY="${CHANGELOG_ENTRY:-New upstream release.}"
MAINTAINER="${MAINTAINER:-Mateus Calixto <noreply@users.noreply.github.com>}"
BUILD="$(mktemp -d)"
ROOT="$BUILD/${PKG}_${VERSION}_all"
trap 'rm -rf "$BUILD"' EXIT

# Application files
install -d "$ROOT/usr/lib/$PKG"
cp -r "$SRC/xfce_theme_manager" "$ROOT/usr/lib/$PKG/"
install -m 644 "$SRC/app.py" "$ROOT/usr/lib/$PKG/app.py"
find "$ROOT/usr/lib/$PKG" -name __pycache__ -prune -exec rm -rf {} +

# Launcher
install -d "$ROOT/usr/bin"
cat > "$ROOT/usr/bin/$PKG" <<LAUNCHER
#!/bin/sh
exec python3 /usr/lib/$PKG/app.py "\$@"
LAUNCHER
chmod 755 "$ROOT/usr/bin/$PKG"

# Menu entry, named after the app id. The X-XFCE-* categories also list it in
# Settings Manager > Personal (StartupWMClass matches the program name set in main())
install -d "$ROOT/usr/share/applications"
cat > "$ROOT/usr/share/applications/$APP_ID.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=XFCE Theme Manager
Name[pt_BR]=Gerenciador de Temas do XFCE
Comment=Manage GTK, XFWM, icon, cursor, Rofi and Mousepad themes, fonts and wallpapers
Comment[pt_BR]=Gerencie temas GTK, XFWM, de ícones, de cursor, Rofi, Mousepad, fontes e papéis de parede
Exec=$PKG
Icon=preferences-desktop-theme
Terminal=false
Categories=Settings;DesktopSettings;GTK;X-XFCE-SettingsDialog;X-XFCE-PersonalSettings;
Keywords=theme;xfwm;icons;cursor;fonts;wallpaper;rofi;mousepad;xfce;tema;fontes;cursores;
StartupWMClass=$PKG
DESKTOP
chmod 644 "$ROOT/usr/share/applications/$APP_ID.desktop"

# AppStream metadata (software centers)
install -d "$ROOT/usr/share/metainfo"
cat > "$ROOT/usr/share/metainfo/$APP_ID.metainfo.xml" <<METAINFO
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>$APP_ID</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>MIT</project_license>
  <name>XFCE Theme Manager</name>
  <summary>Manage XFCE themes, fonts and wallpapers</summary>
  <developer_name>Mateus Calixto</developer_name>
  <description>
    <p>Change GTK, XFWM, icon, cursor, Rofi and Mousepad themes, fonts and wallpapers from a single window, and save combinations as collections.</p>
  </description>
  <launchable type="desktop-id">$APP_ID.desktop</launchable>
  <provides>
    <binary>$PKG</binary>
  </provides>
  <url type="homepage">https://github.com/ogoncas/xfce-themes</url>
  <releases>
    <release version="$VERSION" date="$(date +%F)"/>
  </releases>
</component>
METAINFO
chmod 644 "$ROOT/usr/share/metainfo/$APP_ID.metainfo.xml"

# Docs: copyright and changelog (required by Debian policy)
DOC="$ROOT/usr/share/doc/$PKG"
install -d "$DOC"
cat > "$DOC/copyright" <<COPYRIGHT
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: XFCE Theme Manager
Source: https://github.com/ogoncas/xfce-themes

Files: *
Copyright: Mateus Calixto
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
COPYRIGHT
cat > "$BUILD/changelog" <<CHANGELOG
$PKG ($VERSION) unstable; urgency=low

  * $CHANGELOG_ENTRY

 -- $MAINTAINER  $(date -R)
CHANGELOG
gzip -9n -c "$BUILD/changelog" > "$DOC/changelog.gz"
chmod 644 "$DOC/copyright" "$DOC/changelog.gz"

# Maintainer scripts: byte-compile on install, clean on removal
install -d "$ROOT/DEBIAN"
cat > "$ROOT/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
if [ "$1" = "configure" ] && command -v py3compile >/dev/null 2>&1; then
    py3compile -p xfce-theme-manager /usr/lib/xfce-theme-manager
fi
exit 0
POSTINST
cat > "$ROOT/DEBIAN/prerm" <<'PRERM'
#!/bin/sh
set -e
if command -v py3clean >/dev/null 2>&1; then
    py3clean -p xfce-theme-manager
fi
exit 0
PRERM
chmod 755 "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/prerm"

# Normalize permissions regardless of the umask or the source tree
find "$ROOT" -type d -exec chmod 755 {} +
find "$ROOT/usr/lib" "$ROOT/usr/share" -type f -exec chmod 644 {} +

SIZE="$(du -sk --exclude=DEBIAN "$ROOT" | cut -f1)"
cat > "$ROOT/DEBIAN/control" <<CONTROL
Package: $PKG
Version: $VERSION
Section: x11
Priority: optional
Architecture: all
Installed-Size: $SIZE
Depends: python3, python3-gi, gir1.2-gtk-3.0, gir1.2-gdkpixbuf-2.0, xfconf
Recommends: xfdesktop4, xfwm4, mousepad, rofi
Maintainer: $MAINTAINER
Homepage: https://github.com/ogoncas/xfce-themes
Description: Graphical theme manager for XFCE
 Change GTK/xfwm4 themes, icon and cursor themes, fonts, wallpapers, Rofi
 themes and Mousepad color schemes from a single window, and save
 combinations as collections.
CONTROL

OUT="${OUT:-$SRC/dist}"
mkdir -p "$OUT"
dpkg-deb --root-owner-group -Zxz --build "$ROOT" "$OUT/${PKG}_${VERSION}_all.deb"
