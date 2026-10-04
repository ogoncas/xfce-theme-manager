import os
import subprocess

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


def xfconf_get(channel, prop):
    try:
        out = run(["xfconf-query", "-c", channel, "-p", prop]).stdout.strip()
    except BackendError:
        return None
    return out or None


def xfconf_set(channel, prop, value, vtype="string"):
    # --create adds the property if it does not exist yet
    run(["xfconf-query", "-c", channel, "-p", prop, "--create", "-t", vtype, "-s", value])


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
