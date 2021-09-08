"""Type factories for use with `corgy` (or standalone with `argparse`)."""
import os
from argparse import ArgumentTypeError, FileType
from pathlib import Path
from typing import Generic, IO, Iterator, Literal, Type, TypeVar

__all__ = [
    "OutputFileType",
    "InputFileType",
    "OutputDirectoryType",
    "InputDirectoryType",
    "SubClassType",
]


class OutputFileType(FileType):
    """`argparse.FileType` subclass restricted to write mode.

    Non-existing files are created (including parent directories).

    Args:
        mode: any write mode, e.g., `w` (default), `wb`, `a`, `ab`, etc.
        **kwargs: passed to `argparse.FileType`.
    """

    __metavar__ = "file"

    def __init__(self, mode: str = "w", **kwargs) -> None:
        if "x" in mode or ("r" in mode and "+" not in mode):
            raise ValueError(f"invalid mode for `{type(self)}`: `{mode}`")
        super().__init__(mode, **kwargs)

    def __call__(self, string: str) -> IO:
        if not os.path.exists(filedir := os.path.dirname(string)):
            try:
                os.makedirs(filedir)
            except OSError as e:
                raise ArgumentTypeError(
                    f"could not create parent directory for `{string}`: {e}"
                ) from None
        return super().__call__(string)


class InputFileType(FileType):
    """`argparse.FileType` subclass restricted to read mode.

    This class exists primarily to provide a counterpart to `OutputFileType`.

    Args:
        mode: any read mode, e.g., `r` (default), `rb`, etc.
        **kwargs: passed to `argparse.FileType`.
    """

    __metavar__ = "file"

    def __init__(self, mode: Literal["r", "rb"] = "r", **kwargs) -> None:
        if any(c in mode for c in "wxa+"):
            raise ValueError(f"invalid mode for `{type(self)}`: `{mode}`")
        super().__init__(mode, **kwargs)


class OutputDirectoryType:
    """Factory for creating a type representing a directory to be written to.

    When an instance of this class is called with a string, the string is interpreted as
    a path to a directory. If the directory does not exist, it is created. The directory
    is also checked for write permissions; a `Path` instance is returned if everything
    succeeds, and `argparse.ArgumentTypeError` is raised otherwise.
    """

    __metavar__ = "dir"

    # The type has no state, so it is implemented as a singleton.
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __call__(self, string: str) -> Path:
        if not os.path.exists(string):
            try:
                os.makedirs(string)
            except OSError as e:
                raise ArgumentTypeError(
                    f"could not create directory `{string}`: {e}"
                ) from None
        if not os.path.isdir(string):
            raise ArgumentTypeError(f"`{string}` is not a directory")
        if not os.access(string, os.W_OK):
            raise ArgumentTypeError(f"`{string}` is not writable")
        return Path(string)


class InputDirectoryType:
    """Factory for creating a type representing a directory to be read from.

    When an instance of this class is called with a string, the string is interpreted as
    a path to a directory. A check is performed to ensure that the directory exists, and
    that it is readable. If everything succeeds, a `Path` instance is returned,
    otherwise `argparse.ArgumentTypeError` is raised.
    """

    __metavar__ = "dir"
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __call__(self, string: str) -> Path:
        if not os.path.exists(string):
            raise ArgumentTypeError(f"`{string}` does not exist")
        if not os.path.isdir(string):
            raise ArgumentTypeError(f"`{string}` is not a directory")
        if not os.access(string, os.R_OK):
            raise ArgumentTypeError(f"`{string}` is not readable")
        return Path(string)


_T = TypeVar("_T")


class SubClassType(Generic[_T]):
    """Factory for creating a type representing a sub-class of a given class.

    Args:
        cls: The base class for the type. When used as the `type` argument to an
            `argparse.ArgumentParser.add_argument` call, only sub-classes of this class
            are accepted as valid command-line arguments.
        allow_base: Whether the base class itself is allowed as a valid value for this
            type (default: `False`).
    """

    __metavar__ = "cls"

    def __init__(self, cls: Type[_T], allow_base: bool = False) -> None:
        self.cls = cls
        self.allow_base = allow_base

    @staticmethod
    def _generate_subclasses(base_cls: Type[_T]) -> Iterator[Type[_T]]:
        for subclass in base_cls.__subclasses__():
            if subclass is base_cls:
                continue
            yield subclass
            for subsubclass in SubClassType._generate_subclasses(subclass):
                yield subsubclass

    def __call__(self, string: str) -> Type[_T]:
        if self.cls.__name__ == string and self.allow_base:
            return self.cls
        for subclass in self._generate_subclasses(self.cls):
            if subclass.__name__ == string:
                return subclass
        raise ArgumentTypeError(f"`{string}` is not a valid sub-class of `{self.cls}`")

    def choices(self) -> Iterator[str]:
        """Return an iterator over names of valid choices for this type."""
        if self.allow_base:
            yield self.cls.__name__
        for subclass in self._generate_subclasses(self.cls):
            yield subclass.__name__
