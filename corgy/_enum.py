from __future__ import annotations

from enum import Enum


def is_enum_type(t) -> bool:
    """Check if the argument is `Enum`."""
    try:
        return issubclass(t, Enum)
    except TypeError:
        return False


class EnumWrapper:
    """Wrapper for an `Enum` type.

    This type is used for command line argument parsing; it converts a string
    representation of an enum value to the corresponding enum value.
    """

    enum_type: type[Enum]

    def __init__(self, enum_type):
        self.enum_type = enum_type

    @property
    def __metavar__(self) -> str:
        try:
            return self.enum_type.__metavar__  # type: ignore
        except AttributeError:
            return self.enum_type.__name__

    @property
    def __choices__(self):
        return tuple(self.enum_type.__members__.values())

    def __call__(self, val: str) -> Enum:
        try:
            return self.enum_type[val]
        except KeyError:
            raise ValueError(
                f"{val!r} is not a valid value for {self.enum_type.__name__!r}"
            ) from None
