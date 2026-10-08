import json
import os

from xfce_theme_manager import config
from xfce_theme_manager.backend import common, fonts, rofi, wallpaper
from xfce_theme_manager.backend.mousepad import _style_scheme_id
from xfce_theme_manager.backend.xfwm import collection_xfwm
from xfce_theme_manager.fileio import atomic_write_text
from xfce_theme_manager.locales.en import EN
from xfce_theme_manager.locales.pt_br import PT_BR


def test_locales_have_same_keys():
    assert set(EN) == set(PT_BR)


def test_locales_have_same_placeholders():
    import string
    fmt = string.Formatter()
    for key in EN:
        en = {f for _, f, _, _ in fmt.parse(EN[key]) if f}
        pt = {f for _, f, _, _ in fmt.parse(PT_BR[key]) if f}
        assert en == pt, key


def test_keyfile_set_and_get():
    lines = ["[Other]", "FontName=x", "", "[Configuration]", "A=1", ""]
    out = fonts._keyfile_set(lines, "FontName", "Sans 10")
    assert fonts._keyfile_get(out, "FontName") == "Sans 10"
    assert out[0:2] == ["[Other]", "FontName=x"]
    out = fonts._keyfile_set(out, "FontName", "Mono 9")
    assert fonts._keyfile_get(out, "FontName") == "Mono 9"
    assert fonts._keyfile_get(fonts._keyfile_set([], "K", "v"), "K") == "v"


def test_clean_font_rejects_bad_values():
    for bad in ("", "  ", "a\nb", "x" * 201):
        try:
            fonts._clean_font(bad)
        except common.BackendError:
            continue
        raise AssertionError(bad)
    assert fonts._clean_font(" Sans 10 ") == "Sans 10"


def test_rofi_theme_matches(tmp_path):
    theme = tmp_path / "dark.rasi"
    theme.write_text("")
    assert rofi.rofi_theme_matches(str(theme), str(theme))
    assert rofi.rofi_theme_matches("/x/dark.rasi", "dark")
    assert rofi.rofi_theme_matches("/x/dark.rasi", "dark.rasi")
    assert not rofi.rofi_theme_matches("/x/dark.rasi", "light")
    assert not rofi.rofi_theme_matches("/x/dark.rasi", None)


def test_rofi_set_and_get_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(rofi, "ROFI_CONFIG", str(tmp_path / "config.rasi"))
    weird = '/tmp/a"b\\c/theme.rasi'
    rofi.set_rofi_theme(weird)
    assert rofi.get_current_rofi_theme() == weird
    rofi.set_rofi_theme("/tmp/other.rasi")
    content = (tmp_path / "config.rasi").read_text()
    assert content.count("@theme") == 1


def test_style_scheme_id(tmp_path):
    path = tmp_path / "file-name.xml"
    path.write_text('<?xml version="1.0"?>\n<style-scheme\n  id="real-id" name="X">\n</style-scheme>')
    assert _style_scheme_id(str(path)) == "real-id"
    plain = tmp_path / "plain.xml"
    plain.write_text("<nothing/>")
    assert _style_scheme_id(str(plain)) == "plain"


def test_list_theme_dirs(tmp_path):
    (tmp_path / "A" / "gtk-3.0").mkdir(parents=True)
    (tmp_path / "b" / "gtk-3.0").mkdir(parents=True)
    (tmp_path / ".hidden" / "gtk-3.0").mkdir(parents=True)
    (tmp_path / "none").mkdir()
    assert common.list_theme_dirs([str(tmp_path), "/missing"], "gtk-3.0") == ["A", "b"]


def test_collection_xfwm_legacy_and_explicit():
    assert collection_xfwm({"xfwm": ""}) is None
    assert collection_xfwm({"xfwm": "Foo"}) == "Foo"
    assert collection_xfwm({"gtk": "NotInstalledAnywhere"}) is None


def test_atomic_write_keeps_mode_and_follows_symlink(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("old")
    os.chmod(real, 0o600)
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    atomic_write_text(str(link), "new")
    assert link.is_symlink() and real.read_text() == "new"
    assert oct(real.stat().st_mode & 0o777) == "0o600"


def test_normalize_config_repairs_values():
    cfg = {"language": 5, "titlebar": "x", "wallpaper_folders": ["a", "", 3], "collections": []}
    assert config._normalize_config(cfg)
    assert cfg["language"] == "auto" and cfg["titlebar"] == "header"
    assert cfg["wallpaper_folders"] == ["a"] and cfg["collections"] == {}
    assert not config._normalize_config(cfg)


def test_save_and_load_collections_roundtrip():
    data = {"One": {"gtk": "X", "xfwm": "", "fonts": {"interface": "Sans 10"}}}
    config.save_collections(data)
    assert config.load_collections() == data
    assert json.load(open(config.CONFIG_FILE))["collections"] == data


def test_scan_wallpaper_images_limit_and_dedupe(tmp_path):
    for n in range(5):
        (tmp_path / f"{n}.png").write_bytes(b"")
    (tmp_path / "skip.txt").write_text("")
    (tmp_path / ".hid.png").write_bytes(b"")
    images, truncated = wallpaper.scan_wallpaper_images([str(tmp_path), str(tmp_path)], limit=10)
    assert len(images) == 5 and not truncated
    images, truncated = wallpaper.scan_wallpaper_images([str(tmp_path)], limit=3)
    assert len(images) == 3 and truncated
