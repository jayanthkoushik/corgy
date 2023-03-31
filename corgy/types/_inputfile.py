from __future__ import annotations

import atexit
import sys
from io import BufferedReader, FileIO, TextIOWrapper
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import StrPath

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from ._expand import expand_with_init

__all__ = ("InputTextFile", "InputBinFile")


@expand_with_init
class InputTextFile(TextIOWrapper):
    """`TextIOWrapper` sub-class representing an input file.

    Args:
        path: Path to a file.

    The file must exist, and will be opened in text mode (`r`). `ValueError` is
    raised if this fails. An `atexit` handler will be registered to close the file on
    program termination.
    """

    __metavar__ = "file"
    __slots__ = ()

    def __init__(self, path: StrPath):
        try:
            stream = FileIO(str(path), "r")
        except OSError as e:
            raise ValueError(f"could not open `{path}`: {e}") from None
        buffer = BufferedReader(stream)
        super().__init__(buffer)
        atexit.register(self.__class__.close, self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.buffer.name!r})"

    def __str__(self) -> str:
        return str(self.buffer.name)

    @classmethod
    def stdin_wrapper(cls) -> InputTextFile:
        """`sys.__stdin__` as `InputTextFile`."""
        obj = cls.__new__(cls)
        TextIOWrapper.__init__(obj, sys.__stdin__.buffer, line_buffering=True)
        atexit.register(cls.close, obj)
        return obj


@expand_with_init
class InputBinFile(BufferedReader):
    """Type for an input binary file.

    Args:
        path: Path to a file.

    This class is a thin wrapper around `BufferedReader` that accepts a path, instead
    of a file stream. The file must exist, and will be opened in binary mode.
    `ValueError` is raised if this fails. An `atexit` handler will be registered
    to close the file on program termination.
    """

    __metavar__ = "file"
    __slots__ = ()

    def __init__(self, path: StrPath):
        try:
            stream = FileIO(str(path), "rb")
        except OSError as e:
            raise ValueError(f"could not open `{path}`: {e}") from None
        super().__init__(stream)
        atexit.register(self.__class__.close, self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    def __str__(self) -> str:
        return str(self.name)

    @classmethod
    def stdin_wrapper(cls) -> Self:
        """`sys.__stdin__` as `InputBinFile`."""
        obj = cls.__new__(cls)
        stream = FileIO(sys.__stdin__.fileno(), mode="rb")
        BufferedReader.__init__(obj, stream)
        atexit.register(cls.close, obj)
        return obj
