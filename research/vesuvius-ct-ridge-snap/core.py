from __future__ import annotations

import _core_base as _base
from hardening import install as _install

_install(_base)

for _name in dir(_base):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_base, _name)

del _name
