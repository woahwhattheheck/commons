from __future__ import annotations

"""Hardened core entrypoint for the commercial laundry operations desk.

The retained engine is loaded privately, but its raw class is not left as an
ordinary authority path: direct construction is sealed, hardened operations on
that class delegate to the public facade, and authority-bearing projections are
wrapped with source-literal false authority.  The public core constructor still
routes through the hardened facade so both supported imports share one semantic
surface.
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


def _make_sealed_base_new(raw_base):
    def sealed(cls, *args, **kwargs):
        if cls is raw_base:
            raise TypeError("raw laundry engine is not a public construction surface")
        return object.__new__(cls)

    return sealed


_BaseLaundryDesk.__new__ = staticmethod(_make_sealed_base_new(_BaseLaundryDesk))
del _make_sealed_base_new


def _public_delegate(method_name: str):
    def guarded(self, *args, **kwargs):
        from laundry_desk import LaundryDesk as PublicLaundryDesk

        if not isinstance(self, PublicLaundryDesk):
            raise StateConflict("raw laundry engine operation is not authoritative")
        target = PublicLaundryDesk.__dict__.get(method_name)
        if target is None:
            raise StateConflict("hardened public operation unavailable")
        return target(self, *args, **kwargs)

    guarded.__name__ = method_name
    return guarded


# These operations were hardened by the facade.  Reaching the retained base by
# MRO or a stale handle cannot resurrect their pre-hardening implementations.
for _method_name in (
    "create_daily_route",
    "pickup",
    "deliver",
    "draft_invoice",
    "_insert_exception",
    "render_customer_exports",
):
    setattr(_BaseLaundryDesk, _method_name, _public_delegate(_method_name))


def _authority_projection(original):
    def wrapped(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        result["authority"] = {
            "customer_messaging": False,
            "provider_navigation": False,
            "accounting_mutation": False,
            "payment_mutation": False,
            "deployment": False,
            "revenue_assertion": False,
            "sanitation_certification": False,
            "quality_inference": False,
        }
        return result

    return wrapped


# These retained methods do not mutate authority-bearing state; replacing their
# returned authority with source-literal false values removes dependence on the
# retained function module's rebindable AUTHORITY name, including raw-MRO calls.
_BaseLaundryDesk.route_snapshot = _authority_projection(_BaseLaundryDesk.route_snapshot)
_BaseLaundryDesk.customer_snapshot = _authority_projection(_BaseLaundryDesk.customer_snapshot)
_BaseLaundryDesk.verify_integrity = _authority_projection(_BaseLaundryDesk.verify_integrity)


class LaundryDesk(_BaseLaundryDesk):
    """Compatibility constructor sharing the hardened facade authority surface."""

    def __new__(cls, *args, **kwargs):
        if cls is LaundryDesk:
            from laundry_desk import LaundryDesk as PublicLaundryDesk

            return super().__new__(PublicLaundryDesk)
        return super().__new__(cls)


# The raw class is intentionally absent from the public module namespace.  It is
# still an MRO implementation detail, but direct construction and hardened
# operation calls on it are fail-closed/delegating as above.
del _engine, _loader, _spec, _name, _value, _method_name, _BaseLaundryDesk
