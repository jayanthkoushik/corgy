"""Types for use with `corgy` (or standalone with `argparse`).

An object of the types defined in this module can be created by calling the respective
type class with a single string argument. `ValueError` is raised if the argument can not
be converted to the desired type.

Examples::

    >>> from corgy.types import KeyValuePairs
    >>> StrIntMapType = KeyValuePairs[str, int]
    >>> str_int_map = StrIntMapType("a=1,b=2")
    >>> print(str_int_map)
    {'a': 1, 'b': 2}

    >>> class A: ...
    >>> class B(A): ...
    >>> class C(A): ...

    >>> from corgy.types import SubClass
    >>> ASubClsType = SubClass[A]
    >>> a_subcls = ASubClsType("B")
    >>> a_subcls_obj = a_subcls()
    >>> a_subcls_obj  # doctest: +SKIP
    <B object at 0x106cd93d0>

    >>> from argparse import ArgumentParser, SUPPRESS
    >>> from corgy import CorgyHelpFormatter
    >>> from corgy.types import InputDirectory
    >>> parser = ArgumentParser(
    ...     formatter_class=CorgyHelpFormatter,
    ...     add_help=False,
    ...     usage=SUPPRESS,
    ... )
    >>> _ = parser.add_argument("--d", type=InputDirectory)
    >>> parser.print_help()
    options:
      --d dir  (optional)

"""
from __future__ import annotations

import atexit
import inspect
import os
import sys
import typing
from io import BufferedReader, BufferedWriter, FileIO, TextIOWrapper
from pathlib import Path, PosixPath, WindowsPath
from typing import (
    Dict,
    Generic,
    Iterator,
    List,
    Mapping,
    NoReturn,
    Tuple,
    Type,
    TypeVar,
    Union,
)

if typing.TYPE_CHECKING:
    from _typeshed import StrPath

if sys.version_info >= (3, 9):
    from typing import Literal, Protocol
else:
    from typing_extensions import Literal, Protocol

from ._corgy import Corgy

__all__ = (
    "OutputTextFile",
    "OutputBinFile",
    "LazyOutputTextFile",
    "LazyOutputBinFile",
    "InputTextFile",
    "InputBinFile",
    "OutputDirectory",
    "LazyOutputDirectory",
    "InputDirectory",
    "IODirectory",
    "SubClass",
    "KeyValuePairs",
    "InitArgs",
)


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


def _get_wrapped_buf(cls, buffer):
    """Return an instance of `cls` wrapping `buffer`."""
    # This function is used to implement the `std<in/out/err>_wrapper` class methods
    # in `InputTextFile` and `OutputTextFile`.
    obj_name = f"__{buffer.name}"  # private variable to hold the singleton
    obj = getattr(cls, obj_name, None)
    if obj is None:
        obj = cls.__new__(cls)
        super(cls, obj).__init__(buffer, line_buffering=True)
        atexit.register(cls.close, obj)
        setattr(cls, obj_name, obj)
    return obj


class _OutputTextFileMeta(type):
    # Python < 3.9 does not support `classmethod` combined with `property`,
    # so we need to define class properties as properties on the metaclass.
    @property
    def stdout_wrapper(cls):
        return _get_wrapped_buf(cls, sys.__stdout__.buffer)

    @property
    def stderr_wrapper(cls):
        return _get_wrapped_buf(cls, sys.__stderr__.buffer)


class OutputTextFile(TextIOWrapper, metaclass=_OutputTextFileMeta):
    """`TextIOWrapper` sub-class representing an output file.

    Args:
        path: Path to a file.
        kwargs: Keyword only arguments that are passed to `TextIOWrapper`.

    The file will be created if it does not exist (including any parent directories),
    and opened in text mode (`w`). Existing files will be truncated. `ValueError`
    is raised if any of the operations fail. An `atexit` handler will be registered to
    close the file on program termination.
    """

    __metavar__ = "file"
    __slots__ = ()

    def __init__(self, path: StrPath, **kwargs):
        stream = _get_output_stream(path, "w")
        buffer = BufferedWriter(stream)
        super().__init__(buffer, **kwargs)
        atexit.register(self.__class__.close, self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.buffer.name!r})"

    def __str__(self) -> str:
        return str(self.buffer.name)

    def init(self):
        """No-op for compatibility with `LazyOutputTextFile`."""

    @classmethod  # type: ignore
    @property
    def stdout_wrapper(cls) -> OutputTextFile:
        """`sys.__stdout__` wrapped with `TextIOWrapper` (line buffered)."""
        # For Sphinx.

    @classmethod  # type: ignore
    @property
    def stderr_wrapper(cls) -> OutputTextFile:
        """`sys.__stderr__` wrapped with `TextIOWrapper` (line buffered)."""
        # For Sphinx.


class LazyOutputTextFile(OutputTextFile):
    """`OutputTextFile` sub-class that does not auto-initialize.

    Useful for "default" files, which only need to be created if an alternative is not
    provided. `init` must be called on instances before they can be used.
    """

    __slots__ = ("_path", "_kwargs")

    def __init__(self, path: StrPath, **kwargs):
        # pylint: disable=super-init-not-called
        self._path = path
        self._kwargs = kwargs

    def init(self):
        """Initialize the file."""
        super().__init__(self._path, **self._kwargs)


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


class _InputTextFileMeta(type):
    # Python < 3.9 does not support `classmethod` combined with `property`,
    # so we need to define class properties as properties on the metaclass.
    @property
    def stdin_wrapper(cls):
        return _get_wrapped_buf(cls, sys.__stdin__.buffer)


class InputTextFile(TextIOWrapper, metaclass=_InputTextFileMeta):
    """`TextIOWrapper` sub-class representing an input file.

    Args:
        path: Path to a file.
        kwargs: Keyword only arguments that are passed to `TextIOWrapper`.

    The file must exist, and will be opened in text mode (`r`). `ValueError` is
    raised if this fails. An `atexit` handler will be registered to close the file on
    program termination.
    """

    __metavar__ = "file"
    __slots__ = ()

    def __init__(self, path: StrPath, **kwargs):
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

    @classmethod  # type: ignore
    @property
    def stdin_wrapper(cls) -> InputTextFile:
        """`sys.__stdin__` wrapped with `TextIOWrapper`."""
        # For Sphinx.


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

    def __new__(cls, path: StrPath):  # pylint: disable=arguments-differ
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            raise ValueError(f"could not create directory `{path}`: {e}") from None
        if not os.access(path, os.W_OK):
            raise ValueError(f"`{path}` is not writable")

        # `super().__new__` needs to be called with the os-dependent concrete class.
        cls_ = _WindowsOutputDirectory if os.name == "nt" else _PosixOutputDirectory
        return super().__new__(cls_, path)

    def __repr__(self) -> str:
        return f"OutputDirectory({super().__str__()!r})"

    def init(self):
        """No-op for compatibility with `LazyOutputDirectory`."""


class _WindowsOutputDirectory(OutputDirectory, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _PosixOutputDirectory(OutputDirectory, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()


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
        return Path.__new__(cls_, path)

    def init(self):
        """Initialize the directory."""
        # Just try to create an `OutputDirectory` instance with the same path.
        OutputDirectory(str(self))


class _WindowsLazyOutputDirectory(LazyOutputDirectory, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _PosixLazyOutputDirectory(LazyOutputDirectory, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()


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
        if not os.path.exists(path):
            raise ValueError(f"`{path}` does not exist")
        if not os.path.isdir(path):
            raise ValueError(f"`{path}` is not a directory")
        if not os.access(path, os.R_OK):
            raise ValueError(f"`{path}` is not readable")

        # `super().__new__` needs to be called with the os-dependent concrete class.
        cls_ = _WindowsInputDirectory if os.name == "nt" else _PosixInputDirectory
        return super().__new__(cls_, path)

    def __repr__(self) -> str:
        return f"InputDirectory({super().__str__()!r})"


class _WindowsInputDirectory(InputDirectory, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _PosixInputDirectory(InputDirectory, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()


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
        if not os.path.exists(path):
            raise ValueError(f"`{path}` does not exist")
        if not os.path.isdir(path):
            raise ValueError(f"`{path}` is not a directory")
        if not os.access(path, os.R_OK):
            raise ValueError(f"`{path}` is not readable")
        if not os.access(path, os.W_OK):
            raise ValueError(f"`{path}` is not writable")

        # `super().__new__` needs to be called with the os-dependent concrete class.
        cls_ = _IOWindowsDirectory if os.name == "nt" else _IOPosixDirectory
        return super().__new__(cls_, path)

    def __repr__(self) -> str:
        return f"IODirectory({super().__str__()!r})"


class _IOWindowsDirectory(IODirectory, WindowsPath):
    # pylint: disable=abstract-method
    __slots__ = ()


class _IOPosixDirectory(IODirectory, PosixPath):
    # pylint: disable=abstract-method
    __slots__ = ()


_T = TypeVar("_T")


class _SubClassMeta(type):
    # Python < 3.9 does not support `classmethod` combined with `property`,
    # so we need to define class properties as properties on the metaclass.
    @property
    def __choices__(cls):
        return cls._choices()


class SubClass(Generic[_T], metaclass=_SubClassMeta):
    """Type representing a sub-class of a given class.

    Example::

        >>> from corgy.types import SubClass

        >>> class Base: ...
        >>> class Sub1(Base): ...
        >>> class Sub2(Base): ...

        >>> BaseSubType = SubClass[Base]   # type for a sub-class of `Base`
        >>> BaseSub = BaseSubType("Sub1")  # sub-class of `Base` named `Sub1`
        >>> base_sub = BaseSub()           # instance of a sub-class of `Base`
        >>> base_sub  # doctest: +SKIP
        <Sub1 object at 0x100ea40a0>

    This class cannot be called directly. It first needs to be associated with a base
    class, using the `SubClass[Base]` syntax. This returns a new `SubClass` type, which
    is associated with `Base`. The returned type is callable, and accepts the name of a
    sub-class of `Base`. So, `SubClass[Base]("Sub1")` returns a `SubClass` type instance
    corresponding to the sub-class `Sub1` of `Base`. Finally, the `SubClass` instance
    can be called to create an instance of the sub-class, e.g.,
    `SubClass[Base]("Sub1")()`.

    This class is useful for creating objects of a generic class, where the concrete
    class is determined at runtime, e.g, by a command-line argument::

        >>> from argparse import ArgumentParser

        >>> parser = ArgumentParser()
        >>> _ = parser.add_argument("--base-subcls", type=SubClass[Base])

        >>> args = parser.parse_args(["--base-subcls", "Sub1"])
        >>> base_obj = args.base_subcls()  # an instance of a sub-class of `Base`

    For further convenience when parsing command-line arguments, the class provides a
    `__choices__` property, which returns a tuple of all valid sub-classes, and can be
    passed as the `choices` argument to `ArgumentParser.add_argument`. Refer to the
    docstring of `__choices__` for more information.

    Args:
        name: Name of the sub-class.

    The behavior of sub-class type identification can be customized by setting class
    attributes (preferably on the type returned by the `[...]` syntax).

    * `allow_base`: If `True`, the base class itself will be allowed as a valid
        sub-class. The default is `False`. Example::

            >>> class Base: ...
            >>> class Sub1(Base): ...
            >>> class Sub2(Base): ...
            >>> T = SubClass[Base]
            >>> T.__choices__
            (SubClass[Base]('Sub1'), SubClass[Base]('Sub2'))
            >>> T.allow_base = True
            >>> T.__choices__
            (SubClass[Base]('Base'), SubClass[Base]('Sub1'), SubClass[Base]('Sub2'))

    * `use_full_names`: If `True`, the name passed to the constructor needs to be the
        full name of a sub-class, given by `cls.__module__ + "." + cls.__qualname__`. If
        `False` (the default), the name needs to just be `cls.__name__`. This is useful
        if the sub-classes are not uniquely identified by just their names.

    * `allow_indirect_subs`: If `True` (the default), indirect sub-classes, i.e.,
        sub-classes of the base through another sub-class, are allowed. If `False`,
        only direct sub-classes of the base are allowed. Example::

            >>> class Base: ...
            >>> class Sub1(Base): ...
            >>> class Sub2(Sub1): ...
            >>> T = SubClass[Base]
            >>> T.__choices__
            (SubClass[Base]('Sub1'), SubClass[Base]('Sub2'))
            >>> T.allow_indirect_subs = False
            >>> T.__choices__
            (SubClass[Base]('Sub1'),)

    Note that the types returned by the `SubClass[...]` syntax are cached using the
    base class type. So all instances of `SubClass[Base]` will return the same type,
    and any attributes set on the type will be shared between all instances.
    """

    # The object cache is initialized inside `__class_getitem__`, so every concrete
    # sub-type has its own object cache. The cache uses the sub-class name, along with
    # the class config attributes as key, so that the cache is invalidated when any
    # of the config attributes change.
    _object_cache: Dict[Tuple[str, bool, bool, bool], "SubClass[_T]"]

    allow_base: bool
    use_full_names: bool
    allow_indirect_subs: bool

    _default_allow_base = False
    _default_use_full_names = False
    _default_allow_indirect_subs = True

    _type_cache: Dict[Type[_T], Type[SubClass[_T]]] = {}

    _base: Type[_T]

    _subcls: Type[_T]
    __metavar__ = "cls"
    __slots__ = ("_subcls",)

    def __class_getitem__(cls, item: Type[_T]) -> Type[SubClass[_T]]:
        if hasattr(cls, "_base"):
            raise TypeError(
                f"cannot further sub-script "
                f"`{cls.__name__}[{cls._subclass_name(cls._base)}]`"
            )
        if not hasattr(item, "__subclasses__"):
            raise TypeError(f"`{item}` is not a valid class")

        try:
            ret_type = cls._type_cache[item]
        except (KeyError, TypeError) as e:
            ret_type = type(
                f"{cls.__name__}[{item.__name__}]",
                (cls,),
                {
                    "allow_base": cls._default_allow_base,
                    "use_full_names": cls._default_use_full_names,
                    "allow_indirect_subs": cls._default_allow_indirect_subs,
                    "_base": item,
                    "_object_cache": {},
                    "__slots__": cls.__slots__,
                },
            )
            if not isinstance(e, TypeError):
                # `TypeError` is raised if `item` is not hashable.
                cls._type_cache[item] = ret_type
            sys.modules[ret_type.__module__].__dict__[ret_type.__name__] = ret_type
        return ret_type

    def __getnewargs__(self):
        return (self._subclass_name(self._subcls),)

    @classmethod
    def _ensure_base_set(cls):
        if not hasattr(cls, "_base"):
            raise TypeError(
                f"`{cls.__name__}` must be associated with a base class first: "
                f"use `{cls.__name__}[<class>]`"
            )

    @classmethod
    def _generate_base_subclasses(cls) -> Iterator[Type[_T]]:
        cls._ensure_base_set()

        def _iter_descendants(c):
            for _s in c.__subclasses__():
                yield _s
                yield from _iter_descendants(_s)

        if cls.allow_base:
            yield cls._base

        if cls.allow_indirect_subs:
            yield from _iter_descendants(cls._base)
        else:
            for base_subcls in cls._base.__subclasses__():
                yield base_subcls

    @classmethod
    def _subclass_name(cls, subcls: Type[_T]) -> str:
        if cls.use_full_names:
            return subcls.__module__ + "." + subcls.__qualname__
        return subcls.__name__

    @property
    def which(self) -> Type[_T]:
        """Return the class represented by the `SubClass` instance."""
        return self._subcls

    @classmethod  # type: ignore
    @property
    def __choices__(cls) -> Tuple[SubClass[_T], ...]:
        """Return a tuple of `SubClass` instances for valid sub-classes of the base.

        Each item in the tuple is an instance of `SubClass`, and corresponds to a valid
        sub-class of the base-class associated with this type.
        """
        # For Sphinx.

    @classmethod
    def _choices(cls) -> Tuple[SubClass[_T], ...]:
        cls._ensure_base_set()
        choices: List["SubClass[_T]"] = []
        for subcls in cls._generate_base_subclasses():
            obj = super().__new__(cls)
            obj._subcls = subcls
            choices.append(obj)
        return tuple(choices)

    def __new__(cls, name: str) -> SubClass[_T]:  # pylint: disable=arguments-differ
        cls._ensure_base_set()

        cache_key = (name, cls.allow_base, cls.allow_indirect_subs, cls.use_full_names)
        try:
            return cls._object_cache[cache_key]
        except KeyError:
            pass

        subcls = None
        for subcls in cls._generate_base_subclasses():
            if cls._subclass_name(subcls) == name:
                break
        else:
            if subcls is None:
                raise ValueError(f"`{cls._base}` has no valid sub-classes")
            raise ValueError(f"invalid sub-class name: `{name}`")

        obj = super().__new__(cls)
        obj._subcls = subcls
        cls._object_cache[cache_key] = obj
        return obj

    def __call__(self, *args, **kwargs) -> _T:
        """Return an instance of the sub-class associated with this type.

        Example::

            >>> class Base: ...
            >>> class Sub1(Base):
            ...     def __init__(self, x):
            ...         print(f"initializing `Sub1` with 'x={x}'")

            >>> BaseSubType = SubClass[Base]
            >>> BaseSub = BaseSubType("Sub1")  # an instance of the `SubClass` type

            >>> base_sub = BaseSub(1)
            initializing `Sub1` with 'x=1'

        """
        return self._subcls(*args, **kwargs)  # type: ignore

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SubClass):
            return False
        return self._subcls is other._subcls

    def __hash__(self) -> int:
        return hash(self._subcls)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._subclass_name(self._subcls)!r})"

    def __str__(self) -> str:
        return self._subclass_name(self._subcls)


class _StrMapper(Protocol):
    def __new__(cls, _: str):
        ...


_KT = TypeVar("_KT", bound=_StrMapper)
_VT = TypeVar("_VT", bound=_StrMapper)


class _KeyValuePairsMeta(type):
    # Class properties for `KeyValuePairs`.
    @property
    def __metavar__(cls):
        return cls._metavar()


class KeyValuePairs(  # type: ignore[misc]
    dict, Generic[_KT, _VT], metaclass=_KeyValuePairsMeta
):
    """Dictionary sub-class that is initialized from a string of key-value pairs.

    Example::

        >>> MapType = KeyValuePairs[str, int]
        >>> print(MapType("a=1,b=2"))
        {'a': 1, 'b': 2}

    This class supports the class indexing syntax to specify the types for keys and
    values. `KeyValuePairs[KT, VT]` returns a new `KeyValuePairs` type where the key
    and value types are `KT` and `VT`, respectively. Using the class directly is
    equivalent to using `KeyValuePairs[str, str]`.

    When called, the class expects a single string argument, with comma-separated
    `key=value` pairs (see below for how to change the separators). The string is
    parsed, and a dictionary is created with the keys and values cast to their
    respective types. `ValueError` is raised if this fails. This class is
    useful for parsing dictionaries from command-line arguments.

    By default, the class expects a string of the form `key1=value1,key2=value2,...`.
    This can be changed by setting the following class attributes:

    * sequence_separator: The string that separates individual key-value pairs. The
        default is `,`.

    * item_separator: The string that separates keys and values. The default is `=`.

    Note that types returned by the `KeyValuePairs[...]` syntax are cached using the
    key and value types::

        >>> MapType = KeyValuePairs[str, int]
        >>> MapType.sequence_separator = ";"
        >>> MapType2 = KeyValuePairs[str, int]  # same as `MapType`
        >>> MapType2.sequence_separator
        ';'
        >>> MapType2.sequence_separator = ","

    `KeyValuePairs` instances can also be initialized with a dictionary. However, note
    that the dictionary is not type-checked and is used as-is.
    """

    sequence_separator: str = ","
    item_separator: str = "="

    _kt: Type[_KT]
    _vt: Type[_VT]
    _type_cache: Dict[Tuple[Type[_KT], Type[_VT]], Type[KeyValuePairs[_KT, _VT]]] = {}

    __slots__ = ("_src",)

    def __class_getitem__(  # type: ignore
        cls, item: Tuple[Type[_KT], Type[_VT]]
    ) -> Type[KeyValuePairs[_KT, _VT]]:
        if hasattr(cls, "_kt"):
            raise TypeError(
                f"cannot further sub-script "
                f"`{cls.__name__}[{cls._kt.__name__}, {cls._vt.__name__}]`"
            )

        try:
            ret_type = cls._type_cache[item]
        except (KeyError, TypeError) as e:
            kt, vt = item
            ret_type = type(
                f"{cls.__name__}[{kt.__name__},{vt.__name__}]",
                (cls,),
                {
                    "_kt": kt,
                    "_vt": vt,
                    "sequence_separator": cls.sequence_separator,
                    "item_separator": cls.item_separator,
                    "__slots__": cls.__slots__,
                },
            )
            if not isinstance(e, TypeError):
                # `TypeError` is raised if the item is not hashable.
                cls._type_cache[item] = ret_type
            sys.modules[ret_type.__module__].__dict__[ret_type.__name__] = ret_type
        return ret_type

    @classmethod  # type: ignore
    @property
    def __metavar__(cls) -> str:
        # For Sphinx.
        ...

    @classmethod
    def _metavar(cls) -> str:
        return f"key{cls.item_separator}val{cls.sequence_separator}..."

    def __init__(self, values: Union[str, Mapping[_KT, _VT]]):
        self._src = values

        if isinstance(values, Mapping):
            super().__init__(values)
            return

        kt: Type[_KT] = getattr(self, "_kt", typing.cast(Type[_KT], str))
        vt: Type[_VT] = getattr(self, "_vt", typing.cast(Type[_VT], str))

        if not values:
            super().__init__()
            return

        dic = {}
        for value in values.split(self.sequence_separator):
            try:
                kstr, vstr = value.split(self.item_separator, maxsplit=1)
            except:
                raise ValueError(
                    f"`{value}` is not a valid `{self.item_separator}` separated pair"
                ) from None
            try:
                k = kt(kstr)
            except Exception as e:
                raise ValueError(
                    f"`{kstr}` is not a valid `{kt.__name__}`: {e}"
                ) from None
            try:
                v = vt(vstr)
            except Exception as e:
                raise ValueError(
                    f"`{vstr}` is not a valid `{vt.__name__}`: {e}"
                ) from None
            dic[k] = v
        super().__init__(dic)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._src!r})"

    def __str__(self) -> str:
        return super().__repr__()


class InitArgs(Corgy, Generic[_T]):
    """Corgy wrapper around arguments of a class's `__init__`.

    Example::

        >>> from argparse import ArgumentParser, SUPPRESS
        >>> from typing import Sequence
        >>> from corgy import CorgyHelpFormatter
        >>> from corgy.types import InitArgs

        >>> class Foo:
        ...     def __init__(
        ...         self,
        ...         a: int,
        ...         b: Sequence[str],
        ...         c: float = 0.0,
        ...     ):
        ...         ...

        >>> FooInitArgs = InitArgs[Foo]
        >>> parser = ArgumentParser(
        ...     formatter_class=CorgyHelpFormatter,
        ...     add_help=False,
        ...     usage=SUPPRESS,
        ... )
        >>> FooInitArgs.add_args_to_parser(parser)
        >>> parser.print_help()
        options:
          --a int        (optional)
          --b [str ...]  (optional)
          --c float      (default: 0.0)

        >>> args = parser.parse_args(["--a", "1", "--b", "one", "two"])
        >>> foo = Foo(args.a, args.b, args.c)

    This is a generic class, and on using the `InitArgs[Cls]` syntax, a concrete
    `Corgy` class is created, which has attributes corresponding to the arguments of
    `Cls.__init__`, with types inferred from annotations. The returned class can be used
    as any other `Corgy` class, including as a type annotation within another `Corgy`
    class.

    All arguments of the `__init__` method must be annotated, following the same rules
    as for other `Corgy` classes. Positional only arguments are not supported, since
    they are not associated with an argument name. `TypeError` is raised if either of
    these conditions is not met.
    """

    __slots__ = ()

    def __class_getitem__(cls, item: Type[_T]) -> Type[InitArgs[_T]]:
        item_sig = inspect.signature(item)
        item_annotations, item_defaults = {}, {}
        for param_name, param in item_sig.parameters.items():
            if param.annotation is inspect.Parameter.empty:
                raise TypeError(
                    f"`{item}` is missing annotation for parameter `{param_name}`"
                )

            if param.kind is inspect.Parameter.POSITIONAL_ONLY:
                raise TypeError(
                    f"positional-only paramter `{param_name}` is incompatible with "
                    f"`{cls.__name__}`"
                )

            item_annotations[param_name] = param.annotation
            if param.default is not inspect.Parameter.empty:
                item_defaults[param_name] = param.default

        def new_cls_getitem(newcls, _item: Type[_T]) -> NoReturn:
            raise TypeError(
                f"cannot further sub-script `{newcls.__name__}[{_item.__name__}]`"
            )

        ret_type = type(
            f"{cls.__name__}[{item.__name__}]",
            (cls,),
            {
                "__annotations__": item_annotations,
                "__module__": item.__module__,
                "__class_getitem__": new_cls_getitem,
                **item_defaults,
            },
        )
        sys.modules[ret_type.__module__].__dict__[ret_type.__name__] = ret_type
        return ret_type
