""" README
This __init__.py script defines the public interface for the runex.ops package.
It wraps the submodules dirops, load, and utils, exposing only the attributes
defined in each submodule's `__all__` list.
"""

#%% === Libraries ===

from __future__ import annotations
import sys
import types

#%% === Head ===

# ---------- Imports ----------
from . import dirops as _dirops, utils as _utils

# ---------- Wrapper ----------
def wrap(mod: types.ModuleType) -> types.ModuleType:
    """
    Wraps a module to expose only the names listed in its __all__ attribute.

    Args:
        mod (types.ModuleType): The submodule to wrap.

    Returns:
        types.ModuleType: A proxy module exposing only allowed names.
    """
    allowed = tuple(getattr(mod, "__all__", ()))  # trust the submodule's contract
    proxy = types.ModuleType(mod.__name__, mod.__doc__)
    proxy.__all__ = list(allowed)

    # runtime gate: only allowed names are accessible
    def __getattr__(name: str):
        if name in allowed:
            return getattr(mod, name)
        raise AttributeError(f"module '{proxy.__name__}' has no attribute '{name}'")

    proxy.__getattr__ = __getattr__
    proxy.__dir__ = lambda: sorted(allowed)

    # mirror minimal metadata for tooling
    proxy.__file__ = getattr(mod, "__file__", None)
    proxy.__package__ = getattr(mod, "__package__", None)
    proxy.__spec__ = getattr(mod, "__spec__", None)
    return proxy

#%% === Show Time ===

# ---------- Proxies ----------
dirops  = wrap(_dirops)
utils   = wrap(_utils)

# ---------- Public Exposure ----------
pkg = __name__ + "."
sys.modules[pkg + "dirops"] = dirops
sys.modules[pkg + "utils"] = utils

__all__ = ["dirops", "utils"]

# ---------- Cleanup ----------
del _dirops, _utils
del sys, types
del wrap
del pkg, annotations
