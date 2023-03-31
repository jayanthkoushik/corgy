"""Corgy package for elegant data classes."""

from ._annotations import *
from ._corgy import *
from ._corgyparser import *
from ._helpfmt import *
from ._version import __version__

# pylint: disable=undefined-variable
__all__ = (
    _annotations.__all__  # type: ignore
    + _corgy.__all__  # type: ignore
    + _corgyparser.__all__  # type: ignore
    + _helpfmt.__all__  # type: ignore
)
