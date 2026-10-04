import os
import stat
import tempfile


def atomic_write_text(path, content):
    """Write via a temp file and rename. Follows symlinks (dotfile managers) and keeps permissions."""
    target = os.path.realpath(path)
    directory = os.path.dirname(target)
    os.makedirs(directory, exist_ok=True)
    try:
        mode = stat.S_IMODE(os.stat(target).st_mode)
    except OSError:
        mode = 0o644
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".xtm-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
