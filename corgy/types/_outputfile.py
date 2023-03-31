from __future__ import annotations

import atexit
import os
import sys
from io import BufferedWriter, FileIO, TextIOWrapper
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import StrPath

if sys.version_info >= (3, 9):
    from typing import Literal
else:
    from typing_extensions import Literal
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from ._expand import expand_with_init

__all__ = ("OutputTextFile", "OutputBinFile", "LazyOutputTextFile", "LazyOutputBinFile")


def _get_output_stream(name: StrPath, mode: Literal["w", "wb"]) -> FileIO:
    """Open a file for writing (creating folders if necessary)."""
    filedir = os.path.dirname(name)
    if filedir and not os.path.exists(filedir):
        try:
            os.makedirs(filedir)
        except OSError as e:
            raise ValueError(
                f"could not create parent directory for `{name}`: {e}"
            ) from None
    try:
        return FileIO(str(name), mode)
    except OSError as e:
        raise ValueError(f"could not open `{name}`: {e}") from None


@expand_with_init
class OutputTextFile(TextIOWrapper):
    """`TextIOWrapper` sub-class representing an output file.

    Args:
        path: Path to a file.

    The file will be created if it does not exist (including any parent directories),
    and opened in text mode (`w`). Existing files will be truncated. `ValueError`
    is raised if any of the operations fail. An `atexit` handler will be registered to
    close the file on program termination.
    """

    __metavar__ = "file"
    __slots__ = ()

    def __init__(self, path: StrPath):
        stream = _get_output_stream(path, "w")
        buffer = BufferedWriter(stream)
        super().__init__(buffer)
        atexit.register(self.__class__.close, self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.buffer.name!r})"

    def __str__(self) -> str:
        return str(self.buffer.name)

    def init(self):
        """No-op for compatibility with `LazyOutputTextFile`."""

    @classmethod
    def _stdoe_wrapper(cls, f: TextIOWrapper) -> Self:
        obj = cls.__new__(cls)
        TextIOWrapper.__init__(obj, f.buffer, line_buffering=True)
        atexit.register(cls.close, obj)
        return obj

    @classmethod
    def stdout_wrapper(cls) -> Self:
        """`sys.__stdout__` as `OutputTextFile`."""
        return cls._stdoe_wrapper(sys.__stdout__)

    @classmethod
    def stderr_wrapper(cls) -> Self:
        """`sys.__stderr__` as `OutputTextFile`."""
        return cls._stdoe_wrapper(sys.__stderr__)


@expand_with_init
class LazyOutputTextFile(OutputTextFile):
    """`OutputTextFile` sub-class that does not auto-initialize.

    Useful for "default" files, which only need to be created if an alternative is not
    provided. `init` must be called on instances before they can be used.
    """

    __slots__ = ("_path",)

    def __init__(self, path: StrPath):
        # pylint: disable=super-init-not-called
        self._path = path

    def init(self):
        """Initialize the file."""
        super().__init__(self._path)


@expand_with_init
class OutputBinFile(BufferedWriter):
    """Type for an output binary file.

    Args:
        path: Path to a file.

    This class is a thin wrapper around `BufferedWriter` that accepts a path, instead
    of a file stream. The file will be created if it does not exist (including any
    parent directories), and opened in binary mode. Existing files will be truncated.
    `ValueError` is raised if any of the operations fail. An `atexit` handler
    will be registered to close the file on program termination.
    """

    __metavar__ = "file"
    __slots__ = ()

    def __init__(self, path: StrPath):
        stream = _get_output_stream(path, "wb")
        super().__init__(stream)
        atexit.register(self.__class__.close, self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    def __str__(self) -> str:
        return str(self.name)

    def init(self):
        """No-op for compatibility with `LazyOutputBinFile`."""

    @classmethod
    def _stdoe_wrapper(cls, f: TextIOWrapper) -> Self:
        obj = cls.__new__(cls)
        stream = FileIO(f.fileno(), mode="wb")
        BufferedWriter.__init__(obj, stream)
        atexit.register(cls.close, obj)
        return obj

    @classmethod
    def stdout_wrapper(cls) -> Self:
        """`sys.__stdout__` as `OutputBinFile`."""
        return cls._stdoe_wrapper(sys.__stdout__)

    @classmethod
    def stderr_wrapper(cls) -> Self:
        """`sys.__stderr__` as `OutputBinFile`."""
        return cls._stdoe_wrapper(sys.__stderr__)


@expand_with_init
class LazyOutputBinFile(OutputBinFile):
    """`OutputBinFile` sub-class that does not auto-initialize.

    Useful for "default" files, which only need to be created if an alternative is not
    provided. `init` must be called on instances before they can be used.
    """

    __slots__ = ("_path",)

    def __init__(self, path: StrPath):
        # pylint: disable=super-init-not-called
        self._path = path

    def init(self):
        """Initialize the file."""
        super().__init__(self._path)
