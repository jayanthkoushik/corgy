from __future__ import annotations

import os
from pathlib import Path, PosixPath, WindowsPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import StrPath

from ._expand import expand_with_new

__all__ = ("ReadableFile", "WritableFile")


@expand_with_new
class ReadableFile(Path):
    """`Path` sub-class representing a readable file.

    Args:
        path: String or path-like object.

    The provided path must point to an existing file, and the file must be readable.
    `ValueError` is raised otherwise.
    """

    __metavar__ = "file"
    __slots__ = ()

    def __new__(cls, path: StrPath):  # pylint: disable=arguments-differ
        if not (cls is _WindowsReadableFile or cls is _PosixReadableFile):
            # Check that the path is a file, and that it is readable.
            if not os.path.isfile(path):
                raise ValueError(f"`{path}` is not a file")
            if not os.access(path, os.R_OK):
                raise ValueError(f"`{path}` is not readable")
            cls_ = _WindowsReadableFile if os.name == "nt" else _PosixReadableFile
        else:
            cls_ = cls

        if cls_ is _WindowsReadableFile:
            return WindowsPath.__new__(cls_, path)
        return PosixPath.__new__(cls_, path)

    def __repr__(self) -> str:
        return f"ReadablePath({super().__str__()!r})"


class _WindowsReadableFile(ReadableFile, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _PosixReadableFile(ReadableFile, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()


@expand_with_new
class WritableFile(Path):
    """`Path` sub-class representing a writable file.

    Args:
        path: String or path-like object.

    If the path exists, it must be a file, and it must be writable. If the path does
    not exist, the path's directory must exist and be writable. `ValueError` is
    raised otherwise.
    """

    __metavar__ = "file"
    __slots__ = ()

    def __new__(cls, path: StrPath):  # pylint: disable=arguments-differ
        if not (cls is _WindowsWritableFile or cls is _PosixWritableFile):
            if os.path.exists(path):
                # If the path exists, check that it is a file, and that it is writable.
                if not os.path.isfile(path):
                    raise ValueError(f"`{path}` is not a file")
                if not os.access(path, os.W_OK):
                    raise ValueError(f"`{path}` is not writable")
            else:
                # If the path does not exist, check that the path's directory is
                # writable.
                path_dir = os.path.dirname(path)
                if not path_dir:
                    path_dir = "."
                if not os.access(path_dir, os.W_OK):
                    raise ValueError(f"`{path_dir}` is not writable")

            cls_ = _WindowsWritableFile if os.name == "nt" else _PosixWritableFile
        else:
            cls_ = cls

        if cls_ is _WindowsWritableFile:
            return WindowsPath.__new__(cls_, path)
        return PosixPath.__new__(cls_, path)

    def __repr__(self) -> str:
        return f"WritablePath({super().__str__()!r})"


class _WindowsWritableFile(WritableFile, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _PosixWritableFile(WritableFile, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()
