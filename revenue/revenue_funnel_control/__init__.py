"""Provider-evidence-bound revenue funnel control.

The implementation is loaded lazily so ``python -m revenue.revenue_funnel_control.engine``
does not pre-import the target module through package initialization.
"""

from importlib import import_module

__all__ = ["FunnelError", "compile_bundle", "compile_portfolio", "verify_bundle"]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(name)
    module = import_module(".engine", __name__)
    return getattr(module, name)
