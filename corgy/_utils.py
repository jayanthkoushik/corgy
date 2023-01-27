import sys
from collections.abc import Sequence as AbstractSequence
from typing import Optional, Sequence, Tuple, Union

if sys.version_info >= (3, 10):
    from types import UnionType

if sys.version_info >= (3, 9):
    from typing import Literal
else:
    from typing_extensions import Literal


def _is_union_type(t) -> bool:
    """Check if the argument is a union type."""
    if sys.version_info >= (3, 10):
        # This checks for the `|` based syntax introduced in Python 3.10.
        p310_check = t.__class__ is UnionType
    else:
        p310_check = False
    return p310_check or (hasattr(t, "__origin__") and t.__origin__ is Union)


def _is_optional_type(t) -> bool:
    """Check if the argument is an optional type (i.e. union with None)."""
    if _is_union_type(t):
        _t_args = getattr(t, "__args__", [])
        return len(_t_args) == 2 and _t_args[1] is type(None)
    return False


def _get_concrete_collection_type(type_) -> Optional[type]:
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
    if _is_one_of(type_, Sequence, AbstractSequence):
        return AbstractSequence
    return None


def _is_literal_type(t) -> bool:
    """Check if the argument is `Literal`."""
    return hasattr(t, "__origin__") and t.__origin__ is Literal


def _check_val_type(_val, _type):
    _coll_type = _get_concrete_collection_type(_type)
    if _coll_type is not None:
        if not isinstance(_val, _coll_type):
            raise ValueError(f"invalid value for type '{_type}': {_val!r}")

        if not hasattr(_type, "__args__") or any(
            _type is _bare_type for _bare_type in [Sequence, Tuple]
        ):
            # Untyped collection, e.g., `x: Sequence`.
            return

        _base_types = _type.__args__

        if len(_base_types) == 1:
            # All items in `_val` should match the base type.
            for _val_i in _val:
                _check_val_type(_val_i, _base_types[0])
        elif len(_base_types) == 2 and _base_types[1] is Ellipsis:
            # Same as the previous condition, but `_val` must be non-empty.
            if not _val:
                raise ValueError(f"expected non-empty collection for type '{_type}'")
            for _val_i in _val:
                _check_val_type(_val_i, _base_types[0])
        else:
            # There should be a one-to-one correspondence between items in `_val` and
            # items in `_type`.
            if len(_val) != len(_base_types):
                raise ValueError(
                    f"invalid value for type '{_type}': {_val!r}: "
                    f"expected exactly '{len(_base_types)}' elements"
                )
            for _val_i, _base_type_i in zip(_val, _base_types):
                _check_val_type(_val_i, _base_type_i)

    elif _is_optional_type(_type):
        if _val is None:
            return
        _base_type = _type.__args__[0]
        _check_val_type(_val, _base_type)

    elif _is_literal_type(_type):
        if not hasattr(_type, "__args__") or _val not in _type.__args__:
            raise ValueError(f"invalid value for type '{_type}': {_val!r}")

    elif hasattr(_type, "__choices__"):
        if _val not in _type.__choices__:
            raise ValueError(
                f"invalid value for type '{_type}': {_val!r}: "
                f"expected one of: {_type.__choices__}"
            )

    else:
        try:
            _is_inst = isinstance(_val, _type)
        except TypeError:
            raise ValueError(f"invalid type: {_type}") from None
        if not _is_inst:
            raise ValueError(f"invalid value for type '{_type}': {_val!r}")
