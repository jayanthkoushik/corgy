# pylint: disable=abstract-class-instantiated
import argparse
import sys
from collections.abc import Sequence as AbstractSequence
from typing import List, Optional, Sequence, Set, Tuple, Union

if sys.version_info >= (3, 10):
    from types import UnionType

if sys.version_info >= (3, 9):
    from typing import Literal
else:
    from typing_extensions import Literal

import corgy._corgy  # pylint: disable=cyclic-import


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

    if (
        try_load_corgy_dicts
        and isinstance(_val, dict)
        and isinstance(_type, corgy._corgy._CorgyMeta)
    ):
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


class OptionalTypeAction(argparse.Action):
    """Action for parsing types wrapped in `Optional`."""

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._base_nargs = nargs
        if nargs is None or nargs == 1 or nargs == "?":
            nargs = "?"
        else:
            nargs = "*"
        super().__init__(option_strings, dest, nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        # `values` can be `None`, a single value, or a list of values.
        if values is None:
            setattr(namespace, self.dest, None)
            return

        if isinstance(values, list):
            if not values:
                # Empty list: set to `None`.
                setattr(namespace, self.dest, None)
                return

            # If not empty, check that the list matches the base nargs.
            _len_matches = True
            if self._base_nargs in (None, 1, "?"):
                _len_matches = len(values) == 1
                _err_msg = "expected at most one argument"
            elif isinstance(self._base_nargs, int):
                _len_matches = len(values) == self._base_nargs
                _err_msg = f"expected zero arguments or exactly {self._base_nargs}"
            if not _len_matches:
                raise argparse.ArgumentError(self, _err_msg)

        setattr(namespace, self.dest, values)
