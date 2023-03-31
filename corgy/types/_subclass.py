from __future__ import annotations

import sys
from typing import Dict, Generic, Iterator, List, Tuple, Type, TypeVar

__all__ = ("SubClass",)
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
