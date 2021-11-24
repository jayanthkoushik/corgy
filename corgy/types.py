"""Type factories for use with `corgy` (or standalone with `argparse`)."""
import os
from argparse import ArgumentTypeError, FileType
from pathlib import Path
from typing import Callable, Generic, IO, Iterator, overload, Tuple, Type, TypeVar

__all__ = (
    "OutputFileType",
    "InputFileType",
    "OutputDirectoryType",
    "InputDirectoryType",
    "SubClassType",
    "KeyValueType",
)


class OutputFileType(FileType):
    """`argparse.FileType` subclass restricted to write mode.

    Non-existing files are created (including parent directories).

    Args:
        mode: any write mode, e.g., `w` (default), `wb`, `a`, `ab`, etc.
        **kwargs: passed to `argparse.FileType`.
    """

    __metavar__ = "file"

    def __init__(self, mode: str = "w", **kwargs):
        if "x" in mode or ("r" in mode and "+" not in mode):
            raise ValueError(f"invalid mode for `{type(self)}`: `{mode}`")
        super().__init__(mode, **kwargs)

    def __call__(self, string: str) -> IO:
        filedir = os.path.dirname(string)
        if not os.path.exists(filedir):
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

    def __init__(self, mode: str = "r", **kwargs):
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
        use_full_names: Whether to use the full name of the classes
            (`__module__ + "." + class.__qualname__`) or just `class.__name__`
            (default: `False`). This is useful when the name itself is not enough to
            uniquely identify a sub-class.

    Types returned by this class can be used with `corgy`, and will have the
    sub-classes added as valid choices.
    """

    __metavar__ = "cls"
    __choices__: Tuple[Type[_T], ...]

    def __init__(
        self, cls: Type[_T], allow_base: bool = False, use_full_names: bool = False
    ):
        self.cls = cls
        self.allow_base = allow_base
        self.use_full_names = use_full_names
        self.__choices__ = tuple(self.choices())

    @staticmethod
    def _generate_subclasses(base_cls: Type[_T]) -> Iterator[Type[_T]]:
        for subclass in base_cls.__subclasses__():
            yield subclass
            yield from SubClassType._generate_subclasses(subclass)

    def __corgy_fmt_choice__(self, value: Type[_T]) -> str:
        if self.use_full_names:
            return value.__module__ + "." + value.__qualname__
        return value.__name__

    def __call__(self, string: str) -> Type[_T]:
        if self.__corgy_fmt_choice__(self.cls) == string and self.allow_base:
            return self.cls
        for subclass in self._generate_subclasses(self.cls):
            if self.__corgy_fmt_choice__(subclass) == string:
                return subclass
        raise ArgumentTypeError(f"`{string}` is not a valid sub-class of `{self.cls}`")

    def choices(self) -> Iterator[Type[_T]]:
        """Return an iterator over valid choices for this type."""
        if self.allow_base:
            yield self.cls
        yield from self._generate_subclasses(self.cls)


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class KeyValueType(Generic[_KT, _VT]):
    """Factory for creating a (key, value) pair type.

    When an instance of this class is called with a string of the form `key=value`,
    the string is split on the first `=` character, and the resulting pair is returned,
    after being cast to provided types.

    Args:
        key_type: Callable that convert a string to the key type (default: `str`).
        val_type: Callable that convert a string to the value type (default: `str`)
        separator (keyword only): The separator to use when splitting the input string
            (default: `=`).
    """

    class _MetavarDescriptor:
        """Descriptor to allow `__metavar__` to use the proper separator."""

        def __get__(self, instance: "KeyValueType", _) -> str:
            return f"key{instance.separator}val"

    __metavar__ = _MetavarDescriptor()
    key_type: Callable[[str], _KT]
    val_type: Callable[[str], _VT]
    separator: str

    @overload
    def __new__(cls, *, separator: str = "=") -> "KeyValueType[str, str]":
        ...

    @overload
    def __new__(
        cls,
        key_type: Callable[[str], _KT],
        val_type: Callable[[str], _VT],
        *,
        separator: str = "=",
    ) -> "KeyValueType[_KT, _VT]":
        ...

    def __new__(cls, key_type=str, val_type=str, *, separator="="):
        obj = super().__new__(cls)
        obj.key_type = key_type
        obj.val_type = val_type
        obj.separator = separator
        return obj

    def __call__(self, string: str) -> Tuple[_KT, _VT]:
        try:
            key_s, val_s = string.split(self.separator, 1)
        except ValueError:
            raise ArgumentTypeError(
                f"expected value of form `{self.__metavar__}`: {string}"
            ) from None
        try:
            key = getattr(self, "key_type")(key_s)
        except Exception as e:
            raise ArgumentTypeError(f"could not convert key: {e}") from None
        try:
            val = getattr(self, "val_type")(val_s)
        except Exception as e:
            raise ArgumentTypeError(f"could not convert value: {e}") from None
        return key, val
