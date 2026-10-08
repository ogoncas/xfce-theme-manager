import os
import subprocess
import threading

from gi.repository import Gio, GLib

from ..i18n import _


class BackendError(RuntimeError):
    """Raised when a system setting cannot be read or changed."""


def run(cmd, check=True, timeout=8):
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, check=check, timeout=timeout
        )
    except FileNotFoundError as e:
        raise BackendError(_("err_cmd_missing", cmd=cmd[0])) from e
    except subprocess.TimeoutExpired as e:
        raise BackendError(_("err_cmd_timeout", cmd=cmd[0])) from e
    except subprocess.CalledProcessError as e:
        raise BackendError((e.stderr or "").strip() or str(e)) from e
    except OSError as e:
        raise BackendError(str(e)) from e


# xfconf over D-Bus (no process per call); xfconf-query is the fallback
_XFCONF_NAME = "org.xfce.Xfconf"
_XFCONF_PATH = "/org/xfce/Xfconf"
_XFCONF_ERROR_PREFIX = "org.xfce.Xfconf.Error"
_DBUS_TIMEOUT_MS = 3000
_proxy = None
_proxy_lock = threading.Lock()
_bus_failed = False

_VARIANT_TYPES = {"string": "s", "int": "i", "uint": "u", "bool": "b", "double": "d"}


def _xfconf_proxy():
    global _proxy, _bus_failed
    with _proxy_lock:
        if _proxy is None and not _bus_failed:
            try:
                _proxy = Gio.DBusProxy.new_for_bus_sync(
                    Gio.BusType.SESSION,
                    Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES | Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS,
                    None, _XFCONF_NAME, _XFCONF_PATH, _XFCONF_NAME, None,
                )
            except GLib.Error:
                _bus_failed = True
        return _proxy


class _PropertyNotFound(Exception):
    pass


# Returns the unpacked reply; raises _PropertyNotFound for xfconf errors, GLib.Error if D-Bus is unusable
def _dbus_call(method, params):
    proxy = _xfconf_proxy()
    if proxy is None:
        raise GLib.Error("xfconf D-Bus service unavailable")
    try:
        reply = proxy.call_sync(method, params, Gio.DBusCallFlags.NONE, _DBUS_TIMEOUT_MS, None)
    except GLib.Error as e:
        if Gio.DBusError.is_remote_error(e):
            name = Gio.DBusError.get_remote_error(e) or ""
            if name.startswith(_XFCONF_ERROR_PREFIX):
                raise _PropertyNotFound(e.message) from e
        raise
    return reply.unpack()


def _value_to_text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return value if isinstance(value, str) else str(value)


def xfconf_get(channel, prop):
    try:
        (value,) = _dbus_call("GetProperty", GLib.Variant("(ss)", (channel, prop)))
        return _value_to_text(value) or None
    except _PropertyNotFound:
        return None
    except (GLib.Error, ValueError):
        pass
    try:
        out = run(["xfconf-query", "-c", channel, "-p", prop]).stdout.strip()
    except BackendError:
        return None
    return out or None


def xfconf_list(channel):
    """Return {property: value-as-text} for a whole channel."""
    try:
        (props,) = _dbus_call("GetAllProperties", GLib.Variant("(ss)", (channel, "/")))
        return {key: _value_to_text(value) for key, value in props.items()}
    except _PropertyNotFound:
        return {}
    except (GLib.Error, ValueError):
        pass
    try:
        out = run(["xfconf-query", "-c", channel, "-lv"]).stdout
    except BackendError:
        return {}
    result = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if parts:
            result[parts[0]] = parts[1].strip() if len(parts) > 1 else ""
    return result


def xfconf_set(channel, prop, value, vtype="string"):
    code = _VARIANT_TYPES.get(vtype)
    if code is not None:
        if code in "iu":
            payload = int(value)
        elif code == "b":
            payload = str(value).lower() in ("1", "true")
        elif code == "d":
            payload = float(value)
        else:
            payload = value
        try:
            _dbus_call("SetProperty", GLib.Variant(
                "(ssv)", (channel, prop, GLib.Variant(code, payload))))
            return
        except _PropertyNotFound as e:
            raise BackendError(str(e)) from e
        except (GLib.Error, ValueError):
            pass
    # --set=VALUE keeps values that start with "-" from being read as options
    run(["xfconf-query", "-c", channel, "-p", prop, "--create", "-t", vtype, "--set=" + str(value)])


def process_running(name):
    try:
        entries = os.listdir("/proc")
    except OSError:
        return True
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open("/proc/%s/comm" % entry, encoding="utf-8") as f:
                if f.read().strip() == name:
                    return True
        except OSError:
            continue
    return False


def list_theme_dirs(dirs, marker_subpath):
    themes = set()
    for d in dirs:
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for name in names:
            if not name.startswith(".") and os.path.exists(os.path.join(d, name, marker_subpath)):
                themes.add(name)
    return sorted(themes, key=str.lower)


def find_theme_path(name, dirs, marker):
    for d in dirs:
        candidate = os.path.join(d, name)
        if os.path.exists(os.path.join(candidate, marker)):
            return candidate
    return None


# Themes in extra folders are not on GTK's search path, so symlink them into user_dir
def ensure_searchable(path, standard_dirs, user_dir):
    standard = {os.path.normpath(d) for d in standard_dirs}
    if os.path.normpath(os.path.dirname(os.path.normpath(path))) in standard:
        return
    link = os.path.join(user_dir, os.path.basename(os.path.normpath(path)))
    try:
        if not os.path.lexists(link):
            os.makedirs(user_dir, exist_ok=True)
            os.symlink(os.path.abspath(path), link)
    except OSError:
        pass
