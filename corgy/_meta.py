# pylint: disable=abstract-class-instantiated
from __future__ import annotations

import sys
from collections.abc import Sequence as AbstractSequence
from contextlib import suppress
from typing import Any, ClassVar, List, Optional, Sequence, Set, Tuple, Union

if sys.version_info >= (3, 10):
    from types import UnionType

if sys.version_info >= (3, 9):
    from typing import get_type_hints, Literal
else:
    from typing_extensions import Literal, get_type_hints

from ._annotations import NOT_REQUIRED, REQUIRED
from ._corgyparser import CorgyParser


def is_union_type(t) -> bool:
    """Check if the argument is a union type."""
    # This checks for the `|` based syntax introduced in Python 3.10.
    p310_check = sys.version_info >= (3, 10) and t.__class__ is UnionType
    return p310_check or (hasattr(t, "__origin__") and t.__origin__ is Union)


def is_optional_type(t) -> bool:
    """Check if the argument is an optional type (i.e. union with None)."""
    if is_union_type(t):
        _t_args = getattr(t, "__args__", [])
        return len(_t_args) == 2 and _t_args[1] is type(None)
    return False


def get_concrete_collection_type(type_) -> Optional[type]:
    """Get the base type for objects annotated with the given collection type."""

    def _is_one_of(_t, *_targets) -> bool:
        """Check if a type is any of the target types."""
        if any(_t is _target for _target in _targets):
            return True
        if hasattr(_t, "__origin__"):
            if any(_t.__origin__ is _target for _target in _targets):
                return True
        return False

    if _is_one_of(type_, Tuple, tuple):
        return tuple
    if _is_one_of(type_, List, list):
        return list
    if _is_one_of(type_, Set, set):
        return set
    if _is_one_of(type_, Sequence, AbstractSequence):
        return AbstractSequence
    return None


def is_literal_type(t) -> bool:
    """Check if the argument is `Literal`."""
    return hasattr(t, "__origin__") and t.__origin__ is Literal


def check_val_type(_val, _type, try_cast=False, try_load_corgy_dicts=False):
    _coll_type = get_concrete_collection_type(_type)
    if _coll_type is not None:
        if not isinstance(_val, _coll_type):
            _cast_type = _coll_type if _coll_type is not AbstractSequence else list
            _cast = False
            if try_cast:
                try:
                    _val = _cast_type(_val)
                except TypeError:
                    ...
                else:
                    _cast = True
            if not _cast:
                raise ValueError(f"invalid value for type '{_type}': {_val!r}")
        else:
            _cast_type = type(_val)

        if not hasattr(_type, "__args__") or any(
            _type is _bare_type for _bare_type in [Sequence, Tuple, Set, List]
        ):
            # Untyped collection, e.g., `x: Sequence`.
            return _val

        _base_types = _type.__args__

        _cast_val_is = []
        if len(_base_types) == 1:
            # All items in `_val` should match the base type.
            for _val_i in _val:
                _cast_val_is.append(
                    check_val_type(
                        _val_i, _base_types[0], try_cast, try_load_corgy_dicts
                    )
                )
        elif len(_base_types) == 2 and _base_types[1] is Ellipsis:
            # Same as the previous condition, but `_val` must be non-empty.
            if not _val:
                raise ValueError(f"expected non-empty collection for type '{_type}'")
            for _val_i in _val:
                _cast_val_is.append(
                    check_val_type(
                        _val_i, _base_types[0], try_cast, try_load_corgy_dicts
                    )
                )
        else:
            # There should be a one-to-one correspondence between items in `_val` and
            # items in `_type`.
            if len(_val) != len(_base_types):
                raise ValueError(
                    f"invalid value for type '{_type}': {_val!r}: "
                    f"expected exactly '{len(_base_types)}' elements"
                )
            for _val_i, _base_type_i in zip(_val, _base_types):
                _cast_val_is.append(
                    check_val_type(_val_i, _base_type_i, try_cast, try_load_corgy_dicts)
                )

        _val = _cast_type(_cast_val_is)
        return _val

    if is_optional_type(_type):
        if _val is None:
            return None
        _base_type = _type.__args__[0]
        return check_val_type(_val, _base_type, try_cast, try_load_corgy_dicts)

    if is_literal_type(_type):
        if not hasattr(_type, "__args__") or _val not in _type.__args__:
            raise ValueError(f"invalid value for type '{_type}': {_val!r}")
        return _val

    if hasattr(_type, "__choices__"):
        if _val not in _type.__choices__:
            raise ValueError(
                f"invalid value for type '{_type}': {_val!r}: "
                f"expected one of: {_type.__choices__}"
            )
        return _val

    if try_load_corgy_dicts and isinstance(_val, dict) and isinstance(_type, CorgyMeta):
        return _type.from_dict(_val, try_cast)

    try:
        _is_inst = isinstance(_val, _type)
    except TypeError:
        raise ValueError(f"invalid type: {_type}") from None

    if _is_inst:
        return _val

    _cast = False
    if try_cast:
        try:
            _val = _type(_val)
        except TypeError:
            ...
        else:
            _cast = True
    if not _cast:
        raise ValueError(f"invalid value for type '{_type}': {_val!r}")
    return _val


class CorgyMeta(type):
    """Metaclass for `Corgy`.

    Modifies class creation by parsing type annotations, and creating properties for
    each annotated attribute. Default values and custom parsers are stored in the
    `__defaults` and `__parsers` attributes. Custom flags, if present, are stored in
    the `__flags` attribute. `Required` and `NotRequired` annotations are extracted,
    and required attributes are stored in `__required`.
    """

    __slots__ = ()

    def __new__(cls, name, bases, namespace, **kwds) -> CorgyMeta:
        try:
            _make_slots = kwds.pop("corgy_make_slots")
        except KeyError:
            _make_slots = True

        if _make_slots:
            if "__slots__" not in namespace:
                namespace["__slots__"] = []
            else:
                namespace["__slots__"] = list(namespace["__slots__"])
            namespace["__slots__"].append("__frozen")
        elif "__slots__" in namespace:
            raise TypeError(
                "`__slots__` cannot be defined if `corgy_make_slots` is `False`"
            )

        cls_annotations = namespace.get("__annotations__", {})
        namespace["__annotations__"] = {}
        namespace["__defaults"] = {}
        namespace["__flags"] = {}
        namespace["__parsers"] = {}
        namespace["__helps"] = {}
        namespace["__required"] = set()

        # Temp set of not required attributes--to handle inheritance from
        # non-`Corgy` classes.
        _not_required = set()

        # Extract `corgy_freeze_after_init` (default `False`).
        try:
            namespace["__freeze_after_init"] = kwds.pop("corgy_freeze_after_init")
        except KeyError:
            namespace["__freeze_after_init"] = False

        # See if `corgy_track_bases` is specified (default `True`).
        try:
            _track_bases = kwds.pop("corgy_track_bases")
        except KeyError:
            _track_bases = True
        if _track_bases:
            for base in bases:
                _base_annotations = getattr(base, "__annotations__", {})
                namespace["__annotations__"].update(_base_annotations)
                if isinstance(base, cls):
                    # `base` is also a `Corgy` class.
                    namespace["__defaults"].update(getattr(base, "__defaults"))
                    namespace["__flags"].update(getattr(base, "__flags"))
                    namespace["__parsers"].update(getattr(base, "__parsers"))
                    namespace["__helps"].update(getattr(base, "__helps"))
                    namespace["__required"].update(getattr(base, "__required"))
                    # Add not required attributes to temp set.
                    _base_required = getattr(base, "__required")
                    for _var_name in _base_annotations:
                        if _var_name not in _base_required:
                            _not_required.add(_var_name)
                else:
                    # Fetch default values directly from the base.
                    for _var_name in _base_annotations:
                        try:
                            namespace["__defaults"][_var_name] = getattr(
                                base, _var_name
                            )
                        except AttributeError:
                            pass

        # Add current annotations last, so that they override base values.
        namespace["__annotations__"].update(cls_annotations)

        # See if `corgy_required_by_default` is specified (default `False`).
        try:
            _required_by_default = kwds.pop("corgy_required_by_default")
        except KeyError:
            _required_by_default = False

        tempnew = super().__new__(cls, name, bases, namespace)
        type_hints = get_type_hints(tempnew, include_extras=True)

        if not type_hints:
            return tempnew

        del tempnew  # YUCK
        for var_name in set(namespace["__annotations__"].keys()):
            var_ano = type_hints[var_name]
            # Check for name conflicts.
            _mangled_name = f"_{name.lstrip('_')}__{var_name}"
            if _mangled_name in namespace or _mangled_name in cls_annotations:
                raise TypeError(f"name clash: `{var_name}`, `{_mangled_name}`")

            var_ano_required: Optional[bool]
            var_meta: Optional[Tuple[Any, ...]]
            if hasattr(var_ano, "__origin__") and hasattr(var_ano, "__metadata__"):
                # `<var_name>`: Annotated[<var_type>, <var_flags]`.
                var_type = var_ano.__origin__

                # Check if `_REQUIRED` or `_NOT_REQUIRED` is present.
                # `Required` and `NotRequired` are defined as `Annotated[., _REQUIRED]`,
                # and `Annotated[., _NOT_REQUIRED]`, respectively. Since nested
                # `Annotated` types get flattened, `_REQUIRED` and `_NOT_REQUIRED` will
                # be the last element in `var_meta`.
                if var_ano.__metadata__[-1] in (REQUIRED, NOT_REQUIRED):
                    var_ano_required = var_ano.__metadata__[-1] is REQUIRED
                    var_meta = var_ano.__metadata__[:-1]
                else:
                    var_ano_required = None
                    var_meta = var_ano.__metadata__
            else:
                var_type = var_ano
                var_ano_required = None
                var_meta = None

            if var_meta:
                # `<var_name>: Annotated[<var_type>, <var_help>, [<var_flags>]]`.
                var_help = var_meta[0]
                if not isinstance(var_help, str):
                    raise TypeError(
                        f"incorrect help string annotation for variable `{var_name}`: "
                        f"expected str"
                    )

                if len(var_meta) > 1:
                    if isinstance(var_type, cls):
                        # Custom flags are not allowed for groups.
                        raise TypeError(
                            f"invalid annotation for group `{var_name}`: "
                            f"custom flags not allowed for groups"
                        )

                    var_flags = var_meta[1]
                    if not isinstance(var_flags, list) or not var_flags:
                        raise TypeError(
                            f"incorrect custom flags for variable `{var_name}`: "
                            f"expected non-empty list"
                        )
                else:
                    var_flags = None
            else:
                # `<var_name>: <var_type>`.
                var_help = namespace["__helps"].get(var_name, None)
                var_flags = namespace["__flags"].get(var_name, None)

            if hasattr(var_type, "__origin__") and var_type.__origin__ is ClassVar:
                # Class variable: make sure it has an associated value.
                if var_name not in namespace:
                    if var_name in namespace["__defaults"]:
                        del namespace["__defaults"][var_name]
                    else:
                        raise TypeError(f"class variable `{var_name}` has no value set")
                del namespace["__annotations__"][var_name]
                continue

            # Determine if variable is required or not.
            if var_ano_required is not None:
                _var_required = var_ano_required
            elif var_name not in cls_annotations:
                # Variable was defined in a base class, and is not redefined.
                if var_name in namespace["__required"]:
                    _var_required = True
                elif var_name in _not_required:
                    _var_required = False
                else:
                    # Variable inherited from a non-`Corgy` class.
                    _var_required = _required_by_default
            else:
                _var_required = _required_by_default

            if _var_required:
                namespace["__required"].add(var_name)
            else:
                # Remove from `__required`, in case it was required in a base class.
                namespace["__required"].discard(var_name)

            namespace["__annotations__"][var_name] = var_type

            if var_help is not None:
                namespace["__helps"][var_name] = var_help
            if var_flags is not None:
                namespace["__flags"][var_name] = var_flags

            # Add default value to dedicated dict.
            if var_name in namespace:
                try:
                    check_val_type(namespace[var_name], var_type)
                except ValueError as e:
                    raise ValueError(
                        f"default value type mismatch for '{var_name}'"
                    ) from e
                namespace["__defaults"][var_name] = namespace[var_name]
            elif var_name in namespace["__defaults"] and var_name in cls_annotations:
                # Variable had a default value in a base class, but does not anymore.
                del namespace["__defaults"][var_name]

            # Create `<var_name>` property.
            namespace[var_name] = cls._create_var_property(
                name, var_name, var_type, var_help
            )
            if _make_slots:
                if f"__{var_name}" in namespace["__slots__"]:
                    raise TypeError(
                        f"cannot have slot `__{var_name}`: internal clash with "
                        f"`{var_name}`"
                    )
                namespace["__slots__"].append(f"__{var_name}")

        if _make_slots:
            namespace["__slots__"] = tuple(namespace["__slots__"])

        # Store custom parsers in a dict.
        for _, v in namespace.items():
            if not isinstance(v, CorgyParser):
                continue
            for var_name in v.var_names:
                if (var_name in namespace["__annotations__"]) and isinstance(
                    namespace[var_name], property
                ):
                    namespace["__parsers"][var_name] = v.fparse
                else:
                    raise TypeError(f"invalid target for corgyparser: {var_name}")

        return super().__new__(cls, name, bases, namespace, **kwds)

    @staticmethod
    def _create_var_property(cls_name, var_name, var_type, var_doc) -> property:
        # Properties are stored in private instance variables prefixed with `__`, and
        # must be accessed as `_<cls>__<var_name>`.
        def var_fget(self):
            with suppress(AttributeError):
                return getattr(self, f"_{cls_name.lstrip('_')}__{var_name}")
            raise AttributeError(f"no value available for attribute `{var_name}`")

        def var_fset(self, val):
            if getattr(self, f"_{cls_name.lstrip('_')}__frozen"):
                raise TypeError(f"cannot set `{var_name}`: object is frozen")
            check_val_type(val, var_type)
            setattr(self, f"_{cls_name.lstrip('_')}__{var_name}", val)

        def var_fdel(self):
            if getattr(self, f"_{cls_name.lstrip('_')}__frozen"):
                raise TypeError(f"cannot delete `{var_name}`: object is frozen")
            if var_name in getattr(self, "__required"):
                raise TypeError(f"attribute `{var_name}` cannot be unset")
            delattr(self, f"_{cls_name.lstrip('_')}__{var_name}")

        var_fget.__annotations__ = {"return": var_type}
        var_fset.__annotations__ = {"val": var_type}

        return property(var_fget, var_fset, var_fdel, doc=var_doc)
