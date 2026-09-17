"""Evidence-bound accepted-work-to-cash terminal-action reconciler."""

from importlib import import_module

__all__ = ["ReconcilerError", "compile_bundle", "compile_packet", "verify_bundle"]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(name)
    module = import_module(".engine", __name__)
    return getattr(module, name)
