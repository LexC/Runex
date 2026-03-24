"""Public package surface for ``runex.ops``."""

from __future__ import annotations

import importlib

__all__ = ["ask", "common", "dirops", "lprint", "tabular"]
_LAZY_MODULES = {"ask", "common", "dirops", "lprint", "tabular"}


def __getattr__(name: str):
    if name in _LAZY_MODULES:
        module = importlib.import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
