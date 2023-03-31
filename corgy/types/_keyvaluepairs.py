from __future__ import annotations

import sys
import typing
from typing import Dict, Generic, Mapping, Tuple, Type, TypeVar, Union

if sys.version_info >= (3, 9):
    from typing import Protocol
else:
    from typing_extensions import Protocol

__all__ = ("KeyValuePairs",)


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

        >>> from corgy.types import KeyValuePairs

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
