"""
Runex — Minimal utility toolkit.
Three-layer hierarchy with selected top-level shortcuts.
"""

from __future__ import annotations

import importlib

__all__ = ["ops", "workflow", "DirWiz"]


def __getattr__(name: str):
    if name in {"ops", "workflow"}:
        module = importlib.import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)


def DirWiz(*args, **kwargs):
    """
    Top-level shortcut to the directory wizard main entrypoint.

    Equivalent to: runex.engine.dirwiz.main(*args, **kwargs)
    Imported lazily to avoid exposing `runex.engine` at the package root.
    """
    from .engine.dirwiz import main  # local import prevents `runex.engine` from appearing
    return main(*args, **kwargs)
