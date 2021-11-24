"""Corgy package for elegant command line parsing."""

__all__ = ()

try:
    from ._corgy import *
except ImportError:
    pass
else:
    __all__ += _corgy.__all__  # type: ignore  # pylint: disable=undefined-variable

from ._helpfmt import *

__all__ += _helpfmt.__all__  # type: ignore  # pylint: disable=undefined-variable

from ._version import __version__

_WARN_ABOUT_PY39 = True


def __getattr__(name):
    global _WARN_ABOUT_PY39  # pylint: disable=global-statement

    if name == "Corgy" and _WARN_ABOUT_PY39:
        import sys as _sys

        print("ERROR: `Corgy` requires Python 3.9 or higher\n", file=_sys.stderr)
        _WARN_ABOUT_PY39 = False
    raise AttributeError
