"""Corgy package for elegant command line parsing."""

__all__ = []

try:
    from ._corgy import *
except ImportError:
    pass
else:
    __all__ += _corgy.__all__  # type: ignore # pyling: disable-all

from ._helpfmt import *

__all__ += _helpfmt.__all__  # type: ignore # pylint: disable-all

from ._version import __version__
