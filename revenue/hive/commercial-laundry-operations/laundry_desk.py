from __future__ import annotations

"""Public hardened facade for the commercial laundry operations desk.

The reviewed implementation payload is retained byte-for-byte under a
non-importable ``.disabled`` suffix.  Loading it privately keeps its method
globals out of the public module namespace, so rebinding public informational
constants cannot widen semantic authority while preserving the tested product.
"""

import importlib.machinery as _machinery
import importlib.util as _importlib_util
import sys as _sys
from pathlib import Path as _LoaderPath
from types import MappingProxyType

_PRIVATE_FACADE_NAME = "_commercial_laundry_facade_private"
_PRIVATE_FACADE_PATH = _LoaderPath(__file__).with_name("_laundry_desk_facade_impl.py.disabled")
_loader = _machinery.SourceFileLoader(_PRIVATE_FACADE_NAME, str(_PRIVATE_FACADE_PATH))
_spec = _importlib_util.spec_from_loader(_PRIVATE_FACADE_NAME, _loader)
if _spec is None:
    raise ImportError("unable to load retained commercial-laundry facade")
_facade = _importlib_util.module_from_spec(_spec)
_sys.modules[_PRIVATE_FACADE_NAME] = _facade
try:
    _loader.exec_module(_facade)
finally:
    _sys.modules.pop(_PRIVATE_FACADE_NAME, None)

AUTHORITY = MappingProxyType(
    {
        "customer_messaging": False,
        "provider_navigation": False,
        "accounting_mutation": False,
        "payment_mutation": False,
        "deployment": False,
        "revenue_assertion": False,
        "sanitation_certification": False,
        "quality_inference": False,
    }
)
# Semantic methods in the retained facade resolve this private module global,
# not the public wrapper's rebindable name.
_facade.AUTHORITY = AUTHORITY

for _name, _value in vars(_facade).items():
    if _name not in {"LaundryDesk", "AUTHORITY"} and not _name.startswith("__"):
        globals()[_name] = _value
LaundryDesk = _facade.LaundryDesk

# Do not leave an ordinary module handle that can rebind the retained facade's
# semantic globals. The class's methods retain their private module namespace.
del _facade, _loader, _spec, _name, _value
