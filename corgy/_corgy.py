from __future__ import annotations

import argparse
import importlib
import sys
from collections import defaultdict
from collections.abc import Sequence as AbstractSequence
from contextlib import suppress
from functools import partial
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    IO,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

if sys.version_info >= (3, 10):
    from types import UnionType

if sys.version_info >= (3, 9):
    from typing import get_type_hints, Literal
else:
    from typing_extensions import get_type_hints, Literal

from ._helpfmt import CorgyHelpFormatter

# The main interface is the `Corgy` class. `_CorgyMeta` modifies creation of `Corgy`
# (and its subclasses) by converting annotations to properties, and setting up utilities
# for command line parsing. `corgyparser` is a decorator that allows custom parsers to
# be defined for `Corgy` variables.

__all__ = ("Corgy", "corgyparser")
_T = TypeVar("_T", bound="Corgy")


class BooleanOptionalAction(argparse.Action):
    # :meta private:
    # Backport of `argparse.BooleanOptionalAction` from Python 3.9.
    # Taken almost verbatim from `CPython/Lib/argparse.py`.
    def __init__(self, option_strings, dest, *args, **kwargs):

        _option_strings = []
        for option_string in option_strings:
            _option_strings.append(option_string)

            if option_string.startswith("--"):
                option_string = "--no-" + option_string[2:]
                _option_strings.append(option_string)

        super().__init__(
            option_strings=_option_strings, dest=dest, nargs=0, *args, **kwargs
        )

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string in self.option_strings:
            setattr(namespace, self.dest, not option_string.startswith("--no-"))


class MakeTupleAction(argparse.Action):
    """Action to convert sequence to tuple.

    This is used when adding tuple types to an argument parser, so that the parsed
    sequence is converted to a tuple, and can be set as the value for the corresponding
    attribute.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, tuple(values))


class MakeBoolAction(argparse.Action):
    """Action to convert int to bool.

    This action is used when adding nested bool types (e.g., `Sequence[bool]`) to an
    argument parser. Arguments are added as `int`, and converted to `bool` after
    parsing.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, tuple(map(bool, values)))


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


def _is_tuple_type(t) -> bool:
    """Check if the argument is a tuple type."""
    if t is Tuple or t is tuple:
        return True
    if hasattr(t, "__origin__"):
        if t.__origin__ is Tuple or t.__origin__ is tuple:
            return True
    return False


def _is_sequence_type(t) -> bool:
    """Check if the argument is a generic sequence type."""
    if t is Sequence or t is AbstractSequence:
        return True
    if hasattr(t, "__origin__"):
        if t.__origin__ is Sequence or t.__origin__ is AbstractSequence:
            return True
    return False


def _is_literal_type(t) -> bool:
    """Check if the argument is `Literal`."""
    return hasattr(t, "__origin__") and t.__origin__ is Literal


def _check_val_type(_val, _type):
    _is_seq, _is_tup = _is_sequence_type(_type), _is_tuple_type(_type)
    if _is_seq or _is_tup:
        if (_is_seq and not isinstance(_val, AbstractSequence)) or (
            _is_tup and not isinstance(_val, tuple)
        ):
            raise ValueError(f"invalid value for type '{_type}': {_val}")

        if _type is Sequence or not hasattr(_type, "__args__"):
            # Untyped sequence, e.g., `x: Sequence`.
            return

        _base_types = _type.__args__

        if len(_base_types) == 1:
            # All items in `_val` should match the base type.
            for _val_i in _val:
                _check_val_type(_val_i, _base_types[0])
        elif len(_base_types) == 2 and _base_types[1] is Ellipsis:
            # Same as the previous condition, but `_val` must be non-empty.
            if not _val:
                raise ValueError(f"expected non-empty sequence for type '{_type}'")
            for _val_i in _val:
                _check_val_type(_val_i, _base_types[0])
        else:
            # There should be a one-to-one correspondence between items in `_val` and
            # items in `_type`.
            if len(_val) != len(_base_types):
                raise ValueError(
                    f"invalid value for type '{_type}': {_val}: "
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
            raise ValueError(f"invalid value for type '{_type}': {_val}")

    elif hasattr(_type, "__choices__"):
        if _val not in _type.__choices__:
            raise ValueError(
                f"invalid value for type '{_type}': {_val}: "
                f"expected one of: {_type.__choices__}"
            )

    else:
        try:
            _is_inst = isinstance(_val, _type)
        except TypeError:
            raise ValueError(f"invalid type: {_type}") from None
        if not _is_inst:
            raise ValueError(f"invalid value for type '{_type}': '{_val}'")


class _CorgyMeta(type):
    """Metaclass for `Corgy`.

    Modifies class creation by parsing type annotations, and creating properties for
    each annotated variable. Default values and custom parsers are stored in the
    `__defaults` and `__parsers` attributes. Custom flags, if present, are stored in
    the `__flags` attribute.
    """

    __slots__ = ()

    def __new__(cls, name, bases, namespace, **kwds):
        try:
            _make_slots = kwds.pop("corgy_make_slots")
        except KeyError:
            _make_slots = True

        if _make_slots:
            if "__slots__" not in namespace:
                namespace["__slots__"] = []
            else:
                namespace["__slots__"] = list(namespace["__slots__"])
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

        # See if `corgy_track_bases` is specified (default `True`).
        try:
            _track_bases = kwds["corgy_track_bases"]
        except KeyError:
            _track_bases = True
        else:
            del kwds["corgy_track_bases"]
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

            if hasattr(var_ano, "__origin__") and hasattr(var_ano, "__metadata__"):
                # `<var_name>: Annotated[<var_type>, <var_help>, [<var_flags>]]`.
                var_type = var_ano.__origin__
                var_help = var_ano.__metadata__[0]
                if not isinstance(var_help, str):
                    raise TypeError(
                        f"incorrect help string annotation for variable `{var_name}`: "
                        f"expected str"
                    )

                if len(var_ano.__metadata__) > 1:
                    if isinstance(var_type, cls):
                        # Custom flags are not allowed for groups.
                        raise TypeError(
                            f"invalid annotation for group `{var_name}`: "
                            f"custom flags not allowed for groups"
                        )

                    var_flags = var_ano.__metadata__[1]
                    if not isinstance(var_flags, list) or not var_flags:
                        raise TypeError(
                            f"incorrect custom flags for variable `{var_name}`: "
                            f"expected non-empty list"
                        )
                else:
                    var_flags = None
            elif hasattr(var_ano, "__origin__") and var_ano.__origin__ is ClassVar:
                # `<var_name>: ClassVar[<var_type>]`
                # Make sure the class variable has an associated value.
                if var_name not in namespace:
                    if var_name in namespace["__defaults"]:
                        del namespace["__defaults"][var_name]
                    else:
                        raise TypeError(f"class variable `{var_name}` has no value set")
                del namespace["__annotations__"][var_name]
                continue
            else:
                # `<var_name>: <var_type>`.
                var_type = var_ano
                var_help = namespace["__helps"].get(var_name, None)
                var_flags = namespace["__flags"].get(var_name, None)
            namespace["__annotations__"][var_name] = var_type

            if var_help is not None:
                namespace["__helps"][var_name] = var_help
            if var_flags is not None:
                namespace["__flags"][var_name] = var_flags

            # Add default value to dedicated dict.
            if var_name in namespace:
                try:
                    _check_val_type(namespace[var_name], var_type)
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
            if not isinstance(v, _CorgyParser):
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
            with suppress(KeyError):
                return getattr(self, "__defaults")[var_name]
            raise AttributeError(f"no value available for attribute `{var_name}`")

        def var_fset(self, val):
            _check_val_type(val, var_type)
            setattr(self, f"_{cls_name.lstrip('_')}__{var_name}", val)

        var_fget.__annotations__ = {"return": var_type}
        var_fset.__annotations__ = {"val": var_type}

        return property(var_fget, var_fset, doc=var_doc)


class Corgy(metaclass=_CorgyMeta):
    """Base class for collections of variables.

    To use, subclass `Corgy`, and declare arguments using type annotations::

        class A(Corgy):
            x: int
            y: float

    At runtime, class `A` will have `x`, and `y` as properties, so that the class can be
    used similar to Python dataclasses::

        a = A()
        a.x = 1
        a.y  # AttributeError (y is not set)
        a.y = a.x + 1.1

    Note that the class's `__init__` method only accepts keyword arguments, and ignores
    arguments without a corresponding attribute. The following are all valid::

        A(x=1, y=2.1)
        A(x=1, z=3)  # y is not set, and z is ignored
        A(**{"x": 1, "y": 2.1, "z": 3})

    Attribute values are type-checked, and `ValueError` is raised on type mismatch::

        a = A(x="1")      # ERROR!
        a = A()
        a.x = "1"         # ERROR!

        class A(Corgy):
            x: int = "1"  # ERROR!

    For command line parsing, the `add_args_to_parser` class method can be used to add
    arguments to an `ArgumentParser` object. Refer to the method's documentation for
    more details. `A.add_args_to_parser(parser)` is roughly equivalent to::

        parser.add_argument("--x", type=int, required=True)
        parser.add_argument("--y", type=float, required=True)

    `Corgy` classes have their `__slots__` attribute set to the annotated arguments.
    So, if you want to use additional instance variables not tracked by `Corgy`, define
    them (and only them) in the `__slots__` attribute::

        class A(Corgy):
            __slots__ = ("x",)
            y: float

        a = A()
        a.y = 1  # `Corgy` variable
        a.x = 2  # custom variable

    To allow arbitrary instance variables, add `__dict__` to `__slots__`. Names added
    through custom `__slots__` are not processed by `Corgy`, and will not be added to
    `ArgumentParser` objects by the class methods. Alternatively, to disable setting
    `__slots__` completely, set `corgy_make_slots` to `False` in the class definition::

        class A(Corgy, corgy_make_slots=False):
            y: int

        a = A()
        a.y = 1  # `Corgy` variable
        a.x = 2  # custom variable

    Names marked with the `ClassVar` type will be added as class variables, and will
    not be available as `Corgy` variables::

        class A(Corgy):
            x: ClassVar[int] = 3

        A.x         # OK (returns `3`)
        A.x = 4     # OK
        a = A()
        a.x         # OK (returns `3`)
        a.x = 4     # ERROR!

    Also note that class variables need to be assigned to a value during
    definition, and this value will not be type checked by `Corgy`.

    Inheritance works as expected, whether base classes are themselves `Corgy` classes
    or not, with sub-classes inheriting the attributes of the base class, and overriding
    any redefined attributes::

        class A:
            x: int

        class B(Corgy, A):
            y: float = 1.0
            z: str

        class C(B):
            y: float = 2.0
            z: str
            w: float

        c = C()
        print(c)  # prints C(x=<unset>, y=2.0, z=<unset>, w=<unset>)

    Tracking of base class annotations can be disabled by setting `corgy_track_bases` to
    `False` in the class definition. Properties will still be inherited following
    standard inheritance rules, but `Corgy` will ignore them::

        class A:
            x: int

        class B(Corgy, A, corgy_track_bases=False):
            y: float = 1.0
            z: str

        b = B()
        print(b)  # prints B(y=1.0, z=<unset>)

    `Corgy` classes can themselves be used as a type, to represent a group of
    arguments::

        class A(Corgy):
            x: int
            y: float

        class B(Corgy):
            x: int
            grp: A

    `Corgy` recognizes a number of special annotations, which are used to control how
    the argument is parsed.

    Note:
        If any of the following annotations are unavailable in the Python version being
        used, you can import them from `typing_extensions` (which is available on PyPI).

    **Sequence**
    `collections.abc.Sequence` can be used to annotate sequences of arbitrary types.
    On Python versions below 3.9, `typing.Sequence` must be used instead. Values will be
    checked to ensure that elements match the annotated sequence types.

    There are a few different ways to use `Sequence`, each resulting in different
    validation conditions. The simplest case is a plain (possibly empty) sequence of a
    single type::

        x: Sequence[int]
        x = [1, 2]    # OK
        x = []        # OK
        x = [1, "2"]  # ERROR!
        x = (1, 2)    # OK (any sequence type is allowed)

    The sequence length can be controlled by the arguments to `Sequence`. However, this
    feature is only available in Python 3.9 and above, since `typing.Sequence` only
    accepts a single argument.

    To specify that a sequence must be non-empty, use::

        x: Sequence[int, ...]
        x = []  # ERROR! (`x` cannot be empty)

    Finally, you can specify a fixed-length sequence::

       x: Sequence[int, str, float]
       x = [1]               # ERROR!
       x = [1, "1", 1.0]     # OK
       x = [1, "1", 1.0, 1]  # ERROR!

    **Tuple**
    `typing.Tuple` (or `tuple` in Python 3.9+) can be used instead of `Sequence`. The
    main difference is that values are restricted to be tuples instead of arbitrary
    sequence types. This method is useful in Python versions below 3.9, since
    `typing.Tuple` accepts multiple arguments, unlike `typing.Sequence`.

    **Literal**
    `typing.Literal` can be used to specify that an argument takes one of a fixed set of
    values::

        x: Literal[0, 1, "2"]
        x = 0    # OK
        x = "2"  # OK
        x = "1"  # ERROR!

    `Literal` itself can be used as a type, for instance inside a `Sequence`::

        x: Sequence[Literal[0, 1, 2], Literal[0, 1, 2]]

    This is a sequence of length 2, where each element is either 0, 1, or 2.

    Choices can also be specified by adding a `__choices__` attribute to the argument
    type, containing a sequence of choices::

        class T(int):
            __choices__ = (1, 2)

        x: A
        x = 1  # OK
        x = 3  # ERROR!

    Note that choices specified in this way are not type-checked to ensure that they
    match the argument type.
    """

    @classmethod
    def add_args_to_parser(
        cls,
        parser: argparse._ActionsContainer,
        name_prefix: str = "",
        flatten_subgrps: bool = False,
        defaults: Optional[Mapping[str, Any]] = None,
    ):
        """Add arguments for this class to the given parser.

        Args:
            parser: Argument parser/group to which the class's arguments will be added.
            name_prefix: Prefix for argument names. Arguments will be named
                `--<name-prefix>:<var-name>`. If custom flags are present,
                `--<name-prefix>:<flag>` will be used instead (one for each flag).
            flatten_subgrps: Whether to add sub-groups to the main parser instead of
                creating argument groups. Note: sub-sub-groups are always added with
                this argument set to `True`, since `argparse` in unable to properly
                display nested group arguments.
            defaults: Optional mapping with default values for arguments. Any value
                specified here will override default values specified in the class.
                Values for groups can be specified either as `Corgy` instances, or as
                individual values using the same syntax as for `__init__`.

        Arguments are added based on their type annotations. A number of special
        annotations are recognized, and can be used to control the way an argument
        is parsed.

        **Annotated**:
        `typing.Annotated` can be used to add a help message for an argument::

            x: Annotated[int, "help for x"]

        Annotations can also be used to modify the parser flags for the argument. By
        default, the argument name is used, prefixed with `--`, and `_` replaced by `-`.
        This syntax can also be used to create a positional argument, by specifying a
        flag without any leading `-`::

            x: Annotated[int, "help for x"]  # flag is `--x`
            x: Annotated[int, "help for x", ["-x", "--ex"]]  # flags are `-x/--ex`
            x: Annotated[int, "help for x", ["x"]]  # positional argument

        `Annotated` can accept multiple arguments, but only the first three are used by
        `Corgy`. The first argument is the type, the second is the help message, and the
        third is a list of flags.

        Note:
            `Annotated` should always be the outermost annotation for an argument.

        **Optional**:
        `typing.Optional` can be used to mark an argument as optional::

            x: Optional[int]
            x: int | None  # Python 3.10+ (can also use `Optional`)

        Another way to mark an argument as optional is to provide a default value::

            x: int = 0

        Default values can be used in conjunction with `Optional`::

            x: Optional[int] = 0

        Note that the last two examples are not equivalent, since the type of `x` is
        `Optional[int]` in the last example, so it is allowed to be `None`::

            class A(Corgy):
                x: Optional[int]
                y: int = 0

            a = A()
            a.x = None  # OK
            a.y = None  # ERROR!

        Arguments which are not marked as optional (because they are not annotated with
        `Optional`, and don't have a default value) will added to the parser with
        `required=True`.

        Non-sequence positional arguments marked optional will have `nargs` set to `?`,
        and will accept a single argument or none.

        **bool**
        `bool` types (when not in a sequence) are converted to a pair of options::

            class A(Corgy):
                arg: bool

            parser = ArgumentParser()
            A.add_to_parser(parser)
            parser.print_help()

        Output:

        .. code-block:: text

            usage: -c [-h] --arg | --no-arg

            optional arguments:
            -h, --help       show this help message and exit
            --arg, --no-arg


        **Sequence**
        Sequence types are added to the parser by setting `nargs`. The value for
        `nargs` is determined by the sequence type. Plain sequences, such as
        `Sequence[int]`, will be added with `nargs=*`; Non-empty sequences, such as
        `Sequence[int, ...]`, will be added with `nargs=+`; Finally, fixed-length
        sequences, such as `Sequence[int, int, int]`, will be added with `nargs` set to
        the length of the sequence.

        In all cases, sequence types can only be added to a parser if they are single
        type. Heterogenous sequences, such as `Sequence[int, str]` cannot be added, and
        will raise `ValueError`. Untyped sequences, i.e., annotated with only `Sequence`
        also cannot be added, and will raise `ValueError`.

        **Tuple**
        Tuple types are treated similar to sequences, but will convert the list parsed
        from the command line to a tuple.

        **Literal**
        For `Literal` types, the provided values are passed to the `choices` argument
        of `ArgumentParser.add_argument`. All values must be of the same type, which
        will be inferred from the type of the first value. If the first value has a
        `__bases__` attribute, the type will be inferred as the first base type, and
        all other choices must be subclasses of that type::

            class A: ...
            class A1(A): ...
            class A2(A): ...

            x: Literal[A1, A2]  # inferred type is A

        **`__choices__`**
        For types which specify choices by defining `__choices__`, the values are
        passed to the `choices` argument as with `Literal`, but no type inference is
        performed, and the base type will be used as the argument type.

        **Group**
        Attributes which are themselves `Corgy` types are treated as argument groups.
        Group arguments are added to the command line parser with the group argument
        name prefixed. Note that groups will ignore any custom flags when computing the
        prefix; elements within the group will use custom flags, but because they are
        prefixed with `--`, they will not be positional.

        Example::

            class G(Corgy):
                x: int = 0
                y: float

            class C(Corgy):
                x: int
                g: G

            parser = ArgumentParser()
            C.add_args_to_parser(parser)  # adds `--x`, `--g:x`, and `--g:y`
            # Set default value for `x`.
            C.add_args_to_parser(parser, defaults={"x": 1})
            # Set default value for `g` using a `Corgy` instance.
            # Note that this will override the default value for `x` specified in `G`.
            C.add_args_to_parser(parser, defaults={"g": G(x=1, y=2.0)})
            # Set default value for `g` using individual values.
            C.add_args_to_parser(parser, defaults={"g:y": 2.0})

        Custom parsers:
        Arguments for which a custom parser is defined using `@corgyparser`, will use
        that as the argument type. Refer to the documentation for `corgyparser` for
        details.

        Metavar:
        This function will not explicitly pass a value for the `metavar` argument of
        `ArgumentParser.add_argument`, unless an argument's type has a `__metavar__`
        attribute, in which case, it will be passed as is. To change the metavar for
        arguments with custom parsers, set the `metavar` argument of `corgyparser`.
        """
        base_parser = parser
        base_defaults = getattr(cls, "__defaults").copy()
        if defaults is not None:
            base_defaults.update(defaults)

        # Extract default values for group arguments specified individually using
        # the `<group>:<var name>` syntax.
        group_arg_defaults: Dict[str, Dict[str, Any]] = defaultdict(dict)
        for _k, _v in base_defaults.items():
            if ":" in _k:
                _grp_name, _var_name = _k.split(":")
                group_arg_defaults[_grp_name][_var_name] = _v
            elif _k not in cls.__annotations__:
                raise ValueError(f"default value for unknown argument: `{_k}`")

        for (var_name, var_type) in getattr(cls, "__annotations__").items():
            var_flags = getattr(cls, "__flags").get(
                var_name, [f"--{var_name.replace('_', '-')}"]
            )
            if name_prefix:
                var_flags = [
                    f"--{name_prefix.replace('_', '-')}:{flag.lstrip('-')}"
                    for flag in var_flags
                ]
                var_dest = f"{name_prefix}:{var_name}"
            else:
                var_dest = var_name

            if not any(_flag.startswith("-") for _flag in var_flags):
                var_flags = [var_name]
                var_positional = True
            elif all(_flag.startswith("-") for _flag in var_flags):
                var_positional = False
            else:
                raise TypeError(
                    f"inconsistent positional/optional flags for {var_name}: "
                    f"{var_flags}"
                )

            var_help = getattr(cls, var_name).__doc__  # doc is stored in the property

            # Check if the variable is also `Corgy` type.
            if type(var_type) is type(cls):
                # Create an argument group using `<var_type>`.
                # If there is a default value, pass it using `**defaults`.
                if var_name in base_defaults:
                    try:
                        grp_defaults = base_defaults[var_name].as_dict()
                    except AttributeError:
                        raise ValueError(
                            f"default value for `{var_name}` is not a `Corgy` instance"
                        ) from None
                else:
                    grp_defaults = {}

                # Update defaults with any values specified individually.
                grp_defaults.update(group_arg_defaults.get(var_name, {}))

                grp_parser: argparse._ActionsContainer
                if flatten_subgrps:
                    grp_parser = base_parser
                else:
                    grp_parser = base_parser.add_argument_group(var_dest, var_help)
                var_type.add_args_to_parser(grp_parser, var_dest, True, grp_defaults)
                continue

            # Check if the variable is optional.
            if _is_optional_type(var_type):
                var_base_type = var_type.__args__[0]
                var_required = False
            else:
                var_base_type = var_type
                var_required = var_name not in base_defaults

            # Check if the variable is a sequence.
            var_nargs: Union[int, Literal["+", "*", "?"], None]
            var_action: Optional[Type[argparse.Action]] = None
            _is_sequence = _is_sequence_type(var_base_type)
            _is_tuple = _is_tuple_type(var_base_type)
            if _is_sequence or _is_tuple:
                if (
                    not hasattr(var_base_type, "__args__")
                    or not var_base_type.__args__
                    or isinstance(var_base_type.__args__[0], TypeVar)
                ):
                    raise TypeError(
                        f"`{var_name}` is a sequence, but has no type arguments: "
                        f"use `{var_base_type}[<types>]"
                    )
                if len(var_base_type.__args__) == 1:
                    var_nargs = "*"
                elif (
                    len(var_base_type.__args__) == 2
                    and var_base_type.__args__[1] is Ellipsis
                ):
                    # `...` is used to represent non-empty collections, i.e.,
                    # `Sequence[int, ...]`.
                    var_nargs = "+"
                else:
                    # Ensure single type.
                    if any(
                        _a != var_base_type.__args__[0]
                        for _a in var_base_type.__args__[1:]
                    ):
                        raise TypeError(
                            f"`{var_name}` has unsupported type `{var_base_type}`: only"
                            f" single-type sequences are supported"
                        )
                    var_nargs = len(var_base_type.__args__)
                var_base_type = var_base_type.__args__[0]

                if _is_tuple:
                    # Create a custom action to convert the parsed sequence to a tuple.
                    var_action = MakeTupleAction
            elif var_positional and not var_required:
                # "Optional" positional argument: set `nargs` to `?`.
                var_nargs = "?"
            else:
                var_nargs = None

            # Check if the variable has choices.
            if _is_literal_type(var_base_type):
                # Determine if the first choice has `__bases__`, in which case
                # the first base class is the type for the argument.
                try:
                    c0_type = var_base_type.__args__[0].__bases__[0]
                except AttributeError:
                    c0_type = type(var_base_type.__args__[0])
                    f_check_type: Callable[[Any, Any], bool] = isinstance
                else:
                    f_check_type = issubclass

                # All choices must be of the same type.
                if any(
                    not f_check_type(_a, c0_type) for _a in var_base_type.__args__[1:]
                ):
                    raise TypeError(
                        f"choices for `{var_name}` not all of type `{c0_type}`: "
                        f"`{var_base_type.__args__}`"
                    )
                var_choices = var_base_type.__args__
                var_base_type = c0_type
            elif hasattr(var_base_type, "__choices__"):
                var_choices = var_base_type.__choices__
            else:
                var_choices = None

            var_type_metavar: Optional[str] = getattr(
                var_base_type, "__metavar__", None
            )

            # Check if the variable is boolean. Boolean variables are converted to
            # `--<var-name>`/`--no-<var-name>` arguments.
            if var_base_type is bool and var_nargs is None:
                assert var_action is None
                var_action = BooleanOptionalAction
            elif var_base_type is bool:
                # Nested bool type: add to the parser as `int`, and convert to `bool`
                # after parsing.
                var_action = MakeBoolAction
                var_base_type = int
                var_type_metavar = "bool"

            # Check if the variable has a custom parser.
            _parsers = getattr(cls, "__parsers")
            if var_name in _parsers:
                var_add_type = _parsers[var_name]
                _parser_metavar = getattr(var_add_type, "__metavar__", None)
                if _parser_metavar is not None:
                    var_type_metavar = _parser_metavar
            else:
                var_add_type = var_base_type

            # Add the variable to the parser.
            _kwargs: Dict[str, Any] = {}
            if var_name in getattr(cls, "__flags") and not var_positional:
                _kwargs["dest"] = var_dest
            if var_help is not None:
                _kwargs["help"] = var_help
            if var_nargs is not None:
                _kwargs["nargs"] = var_nargs
            if var_action is not None:
                _kwargs["action"] = var_action
            if var_choices is not None:
                _kwargs["choices"] = var_choices
            if var_name in base_defaults:
                _kwargs["default"] = base_defaults[var_name]
            if var_required and not var_positional:
                _kwargs["required"] = True
            if var_type_metavar is not None:
                _kwargs["metavar"] = var_type_metavar
            parser.add_argument(*var_flags, type=var_add_type, **_kwargs)

    def __init__(self, **args):
        if self.__class__ is Corgy:
            raise TypeError("`Corgy` is an abstract class and cannot be instantiated")

        for arg_name, arg_val in args.items():
            if arg_name in getattr(self, "__annotations__"):
                setattr(self, arg_name, arg_val)

    def _str(self, f_str: Callable[..., str]) -> str:
        s = f"{self.__class__.__name__}("
        i = 0
        for arg_name in getattr(self.__class__, "__annotations__"):
            if i != 0:
                s = s + ", "
            s = s + f"{arg_name}="
            try:
                _val_s = f_str(getattr(self, arg_name))
            except AttributeError:
                _val_s = "<unset>"
            s = s + _val_s
            i += 1
        s = s + ")"
        return s

    def __repr__(self) -> str:
        return self._str(repr)

    def __str__(self) -> str:
        return self._str(str)

    def as_dict(self, recursive: bool = False) -> Dict[str, Any]:
        """Return the object as a dictionary.

        The returned dictionary maps attribute names to their values. Unset attributes
        are omitted, unless they have default values.

        Args:
            recursive: whether to recursively call `as_dict` on attributes which are
                `Corgy` instances. Otherwise, they are returned as is.
        """
        _dict = {}
        for arg_name in getattr(self.__class__, "__annotations__"):
            try:
                _val = getattr(self, arg_name)
            except AttributeError:
                continue
            if recursive and isinstance(_val.__class__, _CorgyMeta):
                _val = _val.as_dict(recursive=True)
            _dict[arg_name] = _val
        return _dict

    @classmethod
    def from_dict(cls: Type[_T], d: Dict[str, Any]) -> _T:
        """Return a new instance of the class using a dictionary.

        This is roughly equivalent to `cls(**d)`, with the main exception being that
        groups can be specified as dictionaries themselves, and will be processed
        recursively.

        Args:
            d: Dictionary to create the instance from.

        Example::

            class A(Corgy):
                x: int
                y: str

            class B(Corgy):
                a: A
                x: str

            # These are all equivalent.
            b = B.from_dict({"x": "three", "a": {"x": 1, "y": "two"}})
            b = B.from_dict({"x": "three", "a": A(x=1, y="two")})
            b = B(x="three", a=A(x=1, y="two"))

        Arguments for groups can also be passed directly in the dictionary by prefixing
        their names with the group name and a colon::

            b = B.from_dict({"x": "three", "a:x": 1, "a:y": "two"})

            class C(Corgy):
                b: B

            c = C.from_dict({"b:x": "three", "b:a:x": 1, "b:a:x": "two"})
        """
        main_args_map = {}
        grp_args_map: Dict[str, Any] = defaultdict(dict)

        for arg_name, arg_val in d.items():
            if ":" in arg_name:
                grp_name, arg_name_base = arg_name.split(":", maxsplit=1)
                if not hasattr(cls, grp_name):
                    raise ValueError(
                        f"invalid argument `{arg_name}`: "
                        f"`{cls}` has no group named `{grp_name}`"
                    )
                if grp_name in d:
                    raise ValueError(
                        f"conflicting arguments: `{arg_name}` and `{grp_name}`"
                    )
                grp_type = getattr(cls, grp_name).fget.__annotations__["return"]
                if not isinstance(grp_type, _CorgyMeta):
                    raise ValueError(f"`{grp_name}` is not a `Corgy` class")
                grp_args_map[grp_name][arg_name_base] = arg_val

            elif hasattr(cls, arg_name):
                arg_type = getattr(cls, arg_name).fget.__annotations__["return"]
                if isinstance(arg_type, _CorgyMeta) and isinstance(arg_val, dict):
                    grp_args_map[arg_name] = arg_val
                else:
                    main_args_map[arg_name] = arg_val

        for grp_name, grp_args in grp_args_map.items():
            grp_type = getattr(cls, grp_name).fget.__annotations__["return"]
            main_args_map[grp_name] = grp_type.from_dict(grp_args)

        return cls(**main_args_map)

    @classmethod
    def parse_from_cmdline(
        cls: Type[_T],
        parser: Optional[argparse.ArgumentParser] = None,
        defaults: Optional[Mapping[str, Any]] = None,
        **parser_args,
    ) -> _T:
        """Return an object of the class parsed from command line arguments.

        Args:
            parser: An instance of `argparse.ArgumentParser` or `None`. If `None`, a new
                instance is created.
            defaults: A dictionary of default values for the arguments, passed to
                `add_args_to_parser`. Refer to the docs for `add_args_to_parser` to
                see more details.
            parser_args: Arguments to be passed to `argparse.ArgumentParser()`. Ignored
                if `parser` is not None.

        Raises:
            ArgumentError: Error parsing command line arguments.
        """
        if parser is None:
            if "formatter_class" not in parser_args:
                parser_args["formatter_class"] = CorgyHelpFormatter
            parser = argparse.ArgumentParser(**parser_args)
        cls.add_args_to_parser(parser, defaults=defaults)
        args = vars(parser.parse_args())
        return cls.from_dict(args)

    @classmethod
    def parse_from_toml(
        cls: Type[_T],
        toml_file: IO[bytes],
        defaults: Optional[Mapping[str, Any]] = None,
    ) -> _T:
        """Parse an object of the class from a toml file.

        Args:
            toml_file: A file-like object containing the class arguments in toml.
            defaults: A dictionary of default values, overriding the any values
                specified in the class.

        Raises:
            TOMLDecodeError: Error parsing the toml file.
        """
        if sys.version_info >= (3, 11):
            tomli = importlib.import_module("tomllib")
        else:
            tomli = importlib.import_module("tomli")
        toml_data = tomli.load(toml_file)
        if defaults is not None:
            for _k, _v in defaults.items():
                if _k not in toml_data:
                    toml_data[_k] = _v
        _parsers = getattr(cls, "__parsers")
        for _k, _v in toml_data.items():
            if _k in _parsers:
                toml_data[_k] = _parsers[_k](_v)
        return cls.from_dict(toml_data)


class _CorgyParser(NamedTuple):
    """Class to represent custom parsers.

    This class is returned by the `@corgyparser` decorator, and is used by `Corgy` to
    keep track of parsers.
    """

    var_names: Sequence[str]
    fparse: Callable[[str], Any]

    def __call__(self, s):
        return self.fparse(s)


def corgyparser(
    *var_names: str, metavar: Optional[str] = None
) -> Callable[[Union[Callable[[str], Any], _CorgyParser]], _CorgyParser]:
    """Decorate a function as a custom parser for one or more variables.

    To use a custom function for parsing an argument with `Corgy`, use this decorator.
    Parsing functions must be static, and should only accept a single string argument.
    Decorating the function with `@staticmethod` is optional, but prevents type errors.
    `@corgyparser` must be the final decorator in the decorator chain.

    Args:
        var_names: The arguments associated with the decorated parser.
        metavar: Keyword only argument to set the metavar when adding the associated
            argument(s) to an `ArgumentParser` instance.

    Example::

        class A(Corgy):
            time: tuple[int, int, int]
            @corgyparser("time", metavar="int int int")
            @staticmethod
            def parse_time(s):
                return tuple(map(int, s.split(":")))

    Multiple arguments can be passed to the decorator, and will all be associated with
    the same parser::

        class A(Corgy):
            x: int
            y: int
            @corgyparser("x", "y")
            @staticmethod
            def parse_x_y(s):
                return int(s)

    The `@corgyparser` decorator can also be chained to use the same parser for multiple
    arguments::

        class A(Corgy):
            x: int
            y: int
            @corgyparser("x")
            @corgyparser("y")
            @staticmethod
            def parse_x_y(s):
                return int(s)

    Note: when chaining, the outer-most non-`None` value of `metavar` will be used.
    """
    if not all(isinstance(_var_name, str) for _var_name in var_names):
        raise TypeError(
            "corgyparser should be passed the name of arguments: decorate using"
            "@corgyparser(<argument(s)>)"
        )

    def wrapper(var_names, metavar, fparse):
        if isinstance(fparse, _CorgyParser):
            corgy_parser = fparse
            corgy_parser.var_names.extend(var_names)
        else:
            if isinstance(fparse, staticmethod):
                fparse = fparse.__func__
            if not callable(fparse):
                raise TypeError("corgyparser can only decorate static functions")
            corgy_parser = _CorgyParser(list(var_names), fparse)

        if metavar is not None:
            corgy_parser.fparse.__metavar__ = metavar
        return corgy_parser

    return partial(wrapper, var_names, metavar)
