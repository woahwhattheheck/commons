from __future__ import annotations

"""Hardened core entrypoint for the commercial laundry operations desk.

The retained engine source is intentionally stored under a non-importable
``.disabled`` suffix.  This module exposes its helper surface for compatibility,
but direct ``LaundryDesk`` construction is routed through the hardened public
facade so there is no ordinary direct-core path around custody/ID/export guards.
"""

import importlib.machinery as _machinery
import importlib.util as _importlib_util
import sys as _sys
from pathlib import Path as _LoaderPath
from types import MappingProxyType

_PRIVATE_ENGINE_NAME = "_commercial_laundry_engine_private"
_PRIVATE_ENGINE_PATH = _LoaderPath(__file__).with_name("_laundry_desk_engine.py.disabled")
_loader = _machinery.SourceFileLoader(_PRIVATE_ENGINE_NAME, str(_PRIVATE_ENGINE_PATH))
_spec = _importlib_util.spec_from_loader(_PRIVATE_ENGINE_NAME, _loader)
if _spec is None:
    raise ImportError("unable to load retained commercial-laundry engine")
_engine = _importlib_util.module_from_spec(_spec)
_sys.modules[_PRIVATE_ENGINE_NAME] = _engine
try:
    _loader.exec_module(_engine)
finally:
    _sys.modules.pop(_PRIVATE_ENGINE_NAME, None)

# Preserve the implementation helper surface used by the compatibility facade,
# without exposing the pre-hardening class or mutable authority object.
for _name, _value in vars(_engine).items():
    if _name not in {"LaundryDesk", "AUTHORITY"} and not _name.startswith("__"):
        globals()[_name] = _value

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
_engine.AUTHORITY = AUTHORITY
_BaseLaundryDesk = _engine.LaundryDesk


class LaundryDesk(_BaseLaundryDesk):
    """Compatibility constructor that cannot bypass the hardened facade."""

    def __new__(cls, *args, **kwargs):
        if cls is LaundryDesk:
            from laundry_desk import LaundryDesk as PublicLaundryDesk

            return super().__new__(PublicLaundryDesk)
        return super().__new__(cls)


# Remove ordinary handles to the retained executable module.  Its class object
# remains only as this class's base so facade subclasses keep the durable engine.
del _engine, _loader, _spec, _name, _value
