from __future__ import annotations

import os
from pathlib import Path, PosixPath, WindowsPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import StrPath

from ._expand import expand_with_new

__all__ = ("OutputDirectory", "LazyOutputDirectory", "InputDirectory", "IODirectory")


@expand_with_new
class OutputDirectory(Path):
    """`Path` sub-class representing a directory to be written to.

    Args:
        path: Path to a directory.

    If the path does not exist, a directory with the path name will be created
    (including any parent directories). `ValueError` is raised if this fails, or
    if the path is not a directory, or if the directory is not writable.
    """

    __metavar__ = "dir"
    __slots__ = ()

    @staticmethod
    def _check_path(path: StrPath):
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            raise ValueError(f"could not create directory `{path}`: {e}") from None
        if not os.access(path, os.W_OK):
            raise ValueError(f"`{path}` is not writable")

    def __new__(cls, path: StrPath):  # pylint: disable=arguments-differ
        if not (cls is _WindowsOutputDirectory or cls is _PosixOutputDirectory):
            cls._check_path(path)
            cls_ = _WindowsOutputDirectory if os.name == "nt" else _PosixOutputDirectory
        else:
            cls_ = cls

        if cls_ is _WindowsOutputDirectory:
            return WindowsPath.__new__(cls_, path)
        return PosixPath.__new__(cls_, path)

    def __repr__(self) -> str:
        return f"OutputDirectory({Path.__str__(self)!r})"

    def init(self):
        """No-op for compatibility with `LazyOutputDirectory`."""


class _WindowsOutputDirectory(OutputDirectory, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _PosixOutputDirectory(OutputDirectory, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()


@expand_with_new
class LazyOutputDirectory(OutputDirectory):
    """`OutputDirectory` sub-class that does not auto-initialize.

    Useful for "default" folders, which only need to be created if an alternative is not
    provided. `init` must be called on instances to ensure that the directory exists.
    """

    __slots__ = ()

    def __new__(cls, path: StrPath):
        cls_ = (
            _WindowsLazyOutputDirectory
            if os.name == "nt"
            else _PosixLazyOutputDirectory
        )
        if cls_ is _WindowsLazyOutputDirectory:
            return WindowsPath.__new__(cls_, path)
        return PosixPath.__new__(cls_, path)

    def init(self):
        """Initialize the directory."""
        self._check_path(self)


class _WindowsLazyOutputDirectory(LazyOutputDirectory, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _PosixLazyOutputDirectory(LazyOutputDirectory, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()


@expand_with_new
class InputDirectory(Path):
    """`Path` sub-class representing a directory to be read from.

    Args:
        path: Path to a directory.

    The directory must exist, and will be checked to ensure it is readable.
    `ValueError` is raised if this is not the case.
    """

    __metavar__ = "dir"
    __slots__ = ()

    def __new__(cls, path: StrPath):  # pylint: disable=arguments-differ
        if not (cls is _WindowsInputDirectory or cls is _PosixInputDirectory):
            if not os.path.exists(path):
                raise ValueError(f"`{path}` does not exist")
            if not os.path.isdir(path):
                raise ValueError(f"`{path}` is not a directory")
            if not os.access(path, os.R_OK):
                raise ValueError(f"`{path}` is not readable")
            cls_ = _WindowsInputDirectory if os.name == "nt" else _PosixInputDirectory
        else:
            cls_ = cls

        if cls_ is _WindowsInputDirectory:
            return WindowsPath.__new__(cls_, path)
        return PosixPath.__new__(cls_, path)

    def __repr__(self) -> str:
        return f"InputDirectory({super().__str__()!r})"


class _WindowsInputDirectory(InputDirectory, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _PosixInputDirectory(InputDirectory, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()


@expand_with_new
class IODirectory(Path):
    """`Path` sub-class representing an existing directory to be read from/written to.

    Args:
        path: Path to a directory.

    The directory must exist, and will be checked to ensure it is readable and
    writeable. `ValueError` is raised if this is not the case.
    """

    __metavar__ = "dir"
    __slots__ = ()

    def __new__(cls, path: StrPath):  # pylint: disable=arguments-differ
        if not (cls is _IOWindowsDirectory or cls is _IOPosixDirectory):
            if not os.path.exists(path):
                raise ValueError(f"`{path}` does not exist")
            if not os.path.isdir(path):
                raise ValueError(f"`{path}` is not a directory")
            if not os.access(path, os.R_OK):
                raise ValueError(f"`{path}` is not readable")
            if not os.access(path, os.W_OK):
                raise ValueError(f"`{path}` is not writable")
            cls_ = _IOWindowsDirectory if os.name == "nt" else _IOPosixDirectory
        else:
            cls_ = cls

        if cls_ is _IOWindowsDirectory:
            return WindowsPath.__new__(cls_, path)
        return PosixPath.__new__(cls_, path)

    def __repr__(self) -> str:
        return f"IODirectory({super().__str__()!r})"


class _IOWindowsDirectory(IODirectory, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _IOPosixDirectory(IODirectory, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()
