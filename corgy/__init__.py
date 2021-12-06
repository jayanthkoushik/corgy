"""Corgy package for elegant command line parsing."""

from ._corgy import *
from ._helpfmt import *
from ._version import __version__

# pylint: disable=undefined-variable
__all__ = _corgy.__all__ + _helpfmt.__all__  # type: ignore
