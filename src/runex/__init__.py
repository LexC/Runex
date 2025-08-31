"""
Runex — Minimal utility toolkit.
Strict hierarchy + selected top-level shortcuts.
"""

from . import ops

def DirWiz(*args, **kwargs):
    """
    Top-level shortcut to the directory wizard main entrypoint.

    Equivalent to: runex.engine.dirwiz.main(*args, **kwargs)
    Imported lazily to avoid exposing `runex.engine` at the package root.
    """
    from .engine.dirwiz import main  # local import prevents `runex.engine` from appearing
    return main(*args, **kwargs)

__all__ = ["ops", "DirWiz"]
