import os
import sys
import tempfile

# Isolated HOME/XDG dirs, set before the package reads them at import time
_tmp = tempfile.mkdtemp(prefix="xtm-test-")
for var, sub in (("HOME", ""), ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                 ("XDG_CACHE_HOME", "cache")):
    path = os.path.join(_tmp, sub) if sub else _tmp
    os.makedirs(path, exist_ok=True)
    os.environ[var] = path
os.environ["XDG_DATA_DIRS"] = os.path.join(_tmp, "sysdata")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
