"""
Runex — Minimal, typed utility functions.
Import once, access everything.
"""

from ._version import __version__

# Re-export everything from engine and ops
from .engine import *   # noqa
from .ops import *      # noqa

__all__ = [
    "__version__",
    *engine.__all__,
    *ops.__all__,
]
