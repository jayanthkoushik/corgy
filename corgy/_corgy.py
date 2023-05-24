from __future__ import annotations

import argparse
import sys
from argparse import (
    _ActionsContainer,
    _StoreConstAction,
    _StoreFalseAction,
    _StoreTrueAction,
    ArgumentParser,
)
from collections import defaultdict
from collections.abc import Sequence as AbstractSequence
from dataclasses import dataclass
from functools import partial
from importlib import import_module
from typing import (
    Any,
    Callable,
    Dict,
    IO,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

if sys.version_info >= (3, 9):
    from typing import Literal
else:
    from typing_extensions import Literal

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from ._actions import BooleanOptionalAction, OptionalTypeAction
from ._corgyparser import CorgyParserAction
from ._helpfmt import CorgyHelpFormatter
from ._meta import (
    check_val_type,
    CorgyMeta,
    get_concrete_collection_type,
    is_literal_type,
    is_optional_type,
)

__all__ = ("Corgy",)
_T = TypeVar("_T", bound="Corgy")


class Corgy(metaclass=CorgyMeta):
    """Base class for collections of attributes.

    To use, subclass `Corgy`, and declare attributes using type annotations::

        >>> from corgy import Corgy

        >>> class A(Corgy):
        ...     x: int
        ...     y: float

    At runtime, class `A` will have `x`, and `y` as properties, so that the class can be
    used similar to Python dataclasses::

        >>> a = A()
        >>> a.x = 1
        >>> a.x
        1

        >>> a.y
        Traceback (most recent call last):
           ...
        AttributeError: no value available for attribute `y`

        >>> a.y = a.x + 1.1
        >>> a.y
        2.1

        >>> del a.x  # unset x
        >>> a.x
        Traceback (most recent call last):
           ...
        AttributeError: no value available for attribute `x`

    Note that the class's `__init__` method only accepts keyword arguments, and ignores
    arguments without a corresponding attribute. The following are all valid::

        >>> A(x=1, y=2.1)
        A(x=1, y=2.1)

        >>> A(x=1, z=3)  # y is not set, and z is ignored
        A(x=1)

        >>> A(**{"x": 1, "y": 2.1, "z": 3})
        A(x=1, y=2.1)

    Attribute values are type-checked, and `ValueError` is raised on type mismatch::

        >>> a = A(x="1")
        Traceback (most recent call last):
            ...
        ValueError: error setting `x`: invalid value for type '<class 'int'>': '1'

        >>> a = A()
        >>> a.x = "1"
        Traceback (most recent call last):
            ...
        ValueError: error setting `x`: invalid value for type '<class 'int'>': '1'

        >>> class A(Corgy):
        ...     x: int = "1"
        Traceback (most recent call last):
            ...
        ValueError: default value type mismatch for 'x'

    Any type which supports type checking with `isinstance` can be used as an
    attribute type (along with some special type annotations that are discussed below).
    This includes other corgy classes::

        >>> class A(Corgy):
        ...     x: int
        ...     y: float

        >>> class B(Corgy):
        ...     x: int
        ...     a: A

        >>> b = B(x=1)
        >>> b.a = A()
        >>> b.a.x = 10
        >>> b
        B(x=1, a=A(x=10))

    `Corgy` classes have their `__slots__` set to the annotated attributes. So, if you
    want to use additional attributes not tracked by `Corgy`, define them (and only
    them) in `__slots__`::

        >>> class A(Corgy):
        ...     __slots__ = ("x",)
        ...     y: int

        >>> a = A()
        >>> a.y = 1  # `Corgy` attribute
        >>> a.x = 2  # custom attribute
        >>> a
        A(y=1)

    To allow arbitrary instance attributes, add `__dict__` to `__slots__`. Names added
    through custom `__slots__` are not processed by `Corgy`. Alternatively, to disable
    setting `__slots__` completely, set `corgy_make_slots` to `False` in the class
    definition::

        >>> class A(Corgy, corgy_make_slots=False):
        ...     y: int

        >>> a = A()
        >>> a.y = 1  # `Corgy` attribute
        >>> a.x = 2  # custom attribute
        >>> a
        A(y=1)

    Names marked with the `ClassVar` type will be added as class variables, and will
    not be available as `Corgy` attributes::

        >>> from typing import ClassVar

        >>> class A(Corgy):
        ...     x: ClassVar[int] = 3

        >>> A.x
        3
        >>> A.x = 4
        >>> A.x
        4
        >>> a = A()
        >>> a.x
        4
        >>> a.x = 5
        Traceback (most recent call last):
            ...
        AttributeError: 'A' object attribute 'x' is read-only

    Also note that class variables need to be assigned to a value during definition, and
    this value will not be type checked by `Corgy`.

    Inheritance works as expected, whether base classes are themselves `Corgy` classes
    or not, with sub-classes inheriting the attributes of the base class, and overriding
    any redefined attributes::

        >>> class A:
        ...     x: int

        >>> class B(Corgy, A):
        ...     y: float = 1.0
        ...     z: str

        >>> class C(B):
        ...     y: float = 2.0
        ...     z: str
        ...     w: float

        >>> c = C()
        >>> print(c)
        C(x=<unset>, y=2.0, z=<unset>, w=<unset>)

    Tracking of base class attributes can be disabled by setting `corgy_track_bases` to
    `False` in the class definition. Properties will still be inherited following
    standard inheritance rules, but `Corgy` will ignore them::

        >>> class A:
        ...     x: int

        >>> class B(Corgy, A, corgy_track_bases=False):
        ...     y: float = 1.0
        ...     z: str

        >>> b = B()
        >>> print(b)
        B(y=1.0, z=<unset>)

    `Corgy` instances can be frozen (preventing any further changes) using the `freeze`
    method. This method can be called automatically after `__init__` by by setting
    `corgy_freeze_after_init` to `True` in the class definition::

        >>> class A(Corgy, corgy_freeze_after_init=True):
        ...    x: int

        >>> a = A(x=1)
        >>> a.x = 2
        Traceback (most recent call last):
            ...
        TypeError: cannot set `x`: object is frozen

    `Corgy` recognizes a number of special annotations, which are used to control how
    attribute values are processed.

    Note:
        If any of the following annotations are unavailable in the Python version being
        used, you can import them from `typing_extensions` (which is available on PyPI).

    *Annotations*
    `typing.Annotated` can be used to add additional metadata to attributes, akin to
    doc strings. It is primarily used to control how attributes are added to
    `ArgumentParser` instances. `typing.Annotated` is stripped on class creation,
    leaving only the base type::

        >>> import sys
        >>> if sys.version_info >= (3, 9):
        ...     from typing import Annotated, Literal
        ... else:
        ...     from typing_extensions import Annotated, Literal

        >>> class A(Corgy):
        ...     x: Annotated[int, "this is x"]

        >>> A.attrs()
        {'x': <class 'int'>}

    `Annotated` should always be the outermost type annotation for an attribute.
    Refer to the docs for `Corgy.add_args_to_parser` for details on usage.

    *Required/NotRequired*
    By default, `Corgy` attributes are not required, and can be unset. This can be
    changed by setting `corgy_required_by_default` to `True` in the class definition::

        >>> class A(Corgy, corgy_required_by_default=True):
        ...     x: int

        >>> A()
        Traceback (most recent call last):
            ...
        ValueError: missing required attribute: `x`
        >>> a = A(x=1)
        >>> del a.x
        Traceback (most recent call last):
            ...
        TypeError: attribute `x` cannot be unset

    Attributes can also explicitly be marked as required/not-required using
    `corgy.Required` and `corgy.NotRequired` annotations::

        >>> from corgy import Required, NotRequired

        >>> class A(Corgy):
        ...     x: Required[int]
        ...     y: NotRequired[int]
        ...     z: int  # not required by default

        >>> a = A(x=1)
        >>> print(a)
        A(x=1, y=<unset>, z=<unset>)

        >>> class B(Corgy, corgy_required_by_default=True):
        ...     x: Required[int]
        ...     y: NotRequired[int]
        ...     z: int

        >>> b = B(x=1, z=2)
        >>> print(b)
        B(x=1, y=<unset>, z=2)

    *Optional*
    Annotating an attribute with `typing.Optional` allows it to be `None`::

        >>> from typing import Optional

        >>> class A(Corgy):
        ...     x: Optional[int]

        >>> a = A()
        >>> a.x = None

    In Python >= 3.10, instead of using `typing.Annotated`, `| None` can be used, i.e.,
    `x: int | None` for example.

    Note that `Optional` is not the same as `NotRequired`. `Optional` allows an
    attribute to be `None`, while `NotRequired` allows an attribute to be unset.
    A `Required` `Optional` attribute will need a value (which can be `None`)::

        >>> class A(Corgy):
        ...     x: Required[Optional[int]]

        >>> A()
        Traceback (most recent call last):
            ...
        ValueError: missing required attribute: `x`
        >>> a = A(x=None)
        >>> print(a)
        A(x=None)

    *Collections*
    Several collection types can be used to annotate attributes, which will restrict the
    type of accepted values. Values in the collection will be checked to ensure that
    they match the annotated collection types. The following collection types are
    supported:

    1. `collections.abc.Sequence` (`typing.Sequence` on Python < 3.9)
    2. `tuple` (`typing.Tuple` on Python < 3.9)
    3. `list` (`typing.List` on Python < 3.9)
    4. `set` (`typing.Set` on Python < 3.9)

    There are a few different ways to use these types, each resulting in different
    validation conditions. The simplest case is a plain (possibly empty) collection of a
    single type::

        >>> from typing import List, Sequence, Set, Tuple

        >>> class A(Corgy):
        ...     x: Sequence[int]
        ...     y: Tuple[str]
        ...     z: Set[float]
        ...     w: List[int]

        >>> a = A()
        >>> a.x = [1, 2]
        >>> a.y = ("1", "2")
        >>> a.z = {1.0, 2.0}
        >>> a.w = [1, 2]
        >>> a
        A(x=[1, 2], y=('1', '2'), z={1.0, 2.0}, w=[1, 2])

        >>> a.x = [1, "2"]
        Traceback (most recent call last):
            ...
        ValueError: error setting `x`: invalid value for type '<class 'int'>': '2'

        >>> a.x = (1, 2)      # `Sequence` accepts any sequence type

        >>> # `Tuple` only accepts tuples
        >>> a.y = ["1", "2"]  # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
            ...
        ValueError: error setting `y`: invalid value for type 'typing.Tuple[str]':
        ['1', '2']

    The collection length can be controlled by the arguments of the type annotation.
    Note, however, that `typing.Sequence/typing.List/typing.Set` do not
    accept multiple arguments, and so, cannot be used if collection length has to be
    specified. On Python < 3.9, only `typing.Tuple` can be used for controlling
    collection lengths.

    To specify that a collection must be non-empty, use ellipsis (`...`) as the second
    argument of the type::

        >>> class A(Corgy):
        ...     x: Tuple[int, ...]

        >>> a = A()
        >>> a.x = tuple()  # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
            ...
        ValueError: error setting `x`: expected non-empty collection for type
        'typing.Tuple[int, ...]'

    Collections can also be restricted to be of a fixed length::

        >>> class A(Corgy):
        ...     x: Tuple[int, str]
        ...     y: Tuple[int, int, int]

        >>> a = A()
        >>> a.x = (1, 1)
        Traceback (most recent call last):
            ...
        ValueError: error setting `x`: invalid value for type '<class 'str'>': 1

        >>> a.y = (1, 1)  # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
            ...
        ValueError: error setting `y`: invalid value for type
        'typing.Tuple[int, int, int]': (1, 1): expected exactly '3' elements

    *Literals*
    `typing.Literal` can be used to specify that an attribute takes one of a fixed set
    of values::

        >>> class A(Corgy):
        ...     x: Literal[0, 1, "2"]

        >>> a = A()
        >>> a.x = 0
        >>> a.x = "2"
        >>> a.x = "1"  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
            ...
        ValueError: error setting `x`: invalid value for type
        'typing.Literal[0, 1, '2']': '1'

    Type annotations can be nested; for instance,
    `Sequence[Literal[0, 1, 2], Literal[0, 1, 2]]` represents a sequence of length 2,
    where each element is either 0, 1, or 2.

    A fixed set of attribute values can also be specified by adding a `__choices__`
    attribute to the argument type, containing a collection of choices::

        >>> class T(int):
        ...     __choices__ = (1, 2)

        >>> class A(Corgy):
        ...     x: T

        >>> a = A()
        >>> a.x = 1
        >>> a.x = 3  # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
            ...
        ValueError: error setting `x`: invalid value for type '<class 'T'>': 3:
        expected one of: (1, 2)

    Note that choices specified in this way are not type-checked to ensure that they
    match the argument type; in the above example, `__choices__` could be set to
    `(1, "2")`.

    *Self*
    `Corgy` classes can have attributes of their own type, annotated using
    `typing.Self`.

        >>> if sys.version_info >= (3, 11):
        ...     from typing import Self
        ... else:
        ...     from typing_extensions import Self

        >>> class C(Corgy):
        ...     x: int
        ...     c: Self

        >>> c = C(x=1)
        >>> c.c = C(x=2)
        >>> c
        C(x=1, c=C(x=2))

        >>> class D(C):
        ...     ...

        >>> c.c = D(x=3)  # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
            ...
        ValueError: error setting `c`: invalid value for type 'Self (bound to
        <class 'C'>)': D(x=3)

    """

    @classmethod
    def add_args_to_parser(
        cls,
        parser: _ActionsContainer,
        name_prefix: str = "",
        flatten_subgrps: bool = False,
        defaults: Optional[Mapping[str, Any]] = None,
    ):
        """Add the class' `Corgy` attributes to the given parser.

        Args:
            parser: Argument parser/group to which the attributes will be added.
            name_prefix: Prefix for argument names. Arguments will be named
                `--<name-prefix>:<attr-name>`. If custom flags are present,
                `--<name-prefix>:<flag>` will be used instead (one for each flag).
            flatten_subgrps: Whether to add sub-groups to the main parser instead of
                creating argument groups. Note: sub-sub-groups are always added with
                this argument set to `True`, since `argparse` in unable to properly
                display nested group arguments.
            defaults: Optional mapping with default values for arguments. Any value
                specified here will override default values specified in the class.
                Values for groups can be specified either as `Corgy` instances, or as
                individual values using the same syntax as for `Corgy.from_dict`.

        Type annotations control how attributes are added to the parser. A number of
        special annotations are parsed and stripped from attribute types to determine
        the parameters for calling `ArgumentParser.add_argument`. These special
        annotations are described below.

        Note: `add_args_to_parser` cannot be used if the type annotation for any
        attribute of the class includes `Self`, unless a custom parser is defined
        for such attributes. See docs for `corgyparser` on how to define custom
        parsers.

        *Annotated*
        `typing.Annotated` can be used to add a help message for the argument::

            >>> import argparse
            >>> from argparse import ArgumentParser
            >>> from corgy import CorgyHelpFormatter

            >>> class A(Corgy):
            ...     x: Annotated[int, "help for x"]

            >>> parser = ArgumentParser(
            ...     formatter_class=CorgyHelpFormatter,
            ...     add_help=False,
            ...     usage=argparse.SUPPRESS,
            ... )

            >>> A.add_args_to_parser(parser)
            >>> parser.print_help()
            options:
              --x int  help for x (optional)

        This annotation can also be used to modify the parser flags for the argument. By
        default, the attribute name is used, prefixed with `--`, and with `_` replaced
        by `-`. If the custom flag does not have a leading `-`, a positional argument
        will be created::

            >>> class A(Corgy):
            ...     x: Annotated[int, "help for x", ["-x", "--ex"]]
            ...     y: Annotated[int, "help for y", ["y"]]

            >>> parser = ArgumentParser(
            ...     formatter_class=CorgyHelpFormatter,
            ...     add_help=False,
            ...     usage=argparse.SUPPRESS,
            ... )

            >>> A.add_args_to_parser(parser)
            >>> parser.print_help()
            positional arguments:
              y int        help for y
            <BLANKLINE>
            options:
              -x/--ex int  help for x (optional)

        `Annotated` can accept multiple arguments, but only the first three are used
        by `Corgy`. The first argument is the attribute type, the second is the help
        message (which must be a string), and the third is a sequence of flags.

        *Required/NotRequired*
        Every corgy attribute is either required or not required. The default status
        depends on the class parameter `corgy_required_by_default` (`False` by default).
        Attributes can also be explicitly marked as required or not required, and will
        control whether the argument will be added with `required=True`::

            >>> from corgy import Required, NotRequired

            >>> class A(Corgy):
            ...     x: Required[int]
            ...     y: NotRequired[int]
            ...     z: int

            >>> parser = ArgumentParser(
            ...     formatter_class=CorgyHelpFormatter,
            ...     add_help=False,
            ...     usage=argparse.SUPPRESS,
            ... )

            >>> A.add_args_to_parser(parser)
            >>> parser.print_help()
            options:
              --x int  (required)
              --y int  (optional)
              --z int  (optional)

        Attributes which are not required, and don't have a default value are added
        with `default=argparse.SUPPRESS`, and so will not be in the parsed namespace::

            >>> parser.parse_args(["--x", "1", "--y", "2"])
            Namespace(x=1, y=2)

        *Optional*
        Attributes marked with `typing.Optional` are allowed to be `None`. The
        arguments for these attributes can be passed with no values (i.e. `--x`
        instead of `--x=1` or `--x 1`) to indicate that the value should be `None`.

        Note: Attributes with default values are also "optional" in the sense that
        they can be omitted from the command line. However, they are not the same as
        attributes marked with `Optional`, since the former are not allowed to be
        `None`. Furthermore, `Required` `Optional` attributes without default values
        _will_ need to be passed on the command line (possibly with no values).

            >>> class A(Corgy):
            ...     x: Required[Optional[int]]

            >>> parser = ArgumentParser()
            >>> A.add_args_to_parser(parser)
            >>> parser.parse_args(["--x"])
            Namespace(x=None)

        *Boolean*
        `bool` types (when not in a collection) are converted to a pair of options::

            >>> class A(Corgy):
            ...     arg: bool

            >>> parser = ArgumentParser(
            ...     formatter_class=CorgyHelpFormatter,
            ...     add_help=False,
            ...     usage=argparse.SUPPRESS,
            ... )

            >>> A.add_args_to_parser(parser)
            >>> parser.print_help()
            options:
              --arg/--no-arg

        *Collection*
        Collection types are added to the parser by setting `nargs`. The value for
        `nargs` is determined by the collection type. Plain collections, such as
        `Sequence[int]`, will be added with `nargs=*`; Non-empty collections, such as
        `Sequence[int, ...]`, will be added with `nargs=+`; Finally, fixed-length
        collections, such as `Sequence[int, int, int]`, will be added with `nargs` set
        to the length of the collection.

        In all cases, collection types can only be added to a parser if they are single
        type. Heterogenous collections, such as `Sequence[int, str]` cannot be added,
        and will raise `ValueError`. Untyped collections (e.g., `x: Sequence`), also
        cannot be added.

        Arguments for optional collections will also accept no values to indicate
        `None`. Due to this, it is not possible to parse an empty collection for
        an optional collection argument::

            >>> class A(Corgy):
            ...     x: Optional[Sequence[int]]
            ...     y: Sequence[int]

            >>> parser = ArgumentParser()
            >>> A.add_args_to_parser(parser)
            >>> parser.parse_args(["--x", "--y"])
            Namespace(x=None, y=[])

        *Literal*
        For `Literal` types, the provided values are passed to the `choices` argument
        of `ArgumentParser.add_argument`. All values must be of the same type, which
        will be inferred from the type of the first value. If the first value has a
        `__bases__` attribute, the type will be inferred as the first base type, and
        all other choices must be subclasses of that type::

            >>> class T: ...
            >>> class T1(T): ...
            >>> class T2(T): ...

            >>> class A(Corgy):
            ...     x: Literal[T1, T2]

            >>> parser = ArgumentParser(
            ...     formatter_class=CorgyHelpFormatter,
            ...     add_help=False,
            ...     usage=argparse.SUPPRESS,
            ... )

            >>> A.add_args_to_parser(parser)
            >>> parser.print_help()
            options:
              --x T  ({T1/T2} optional)

        For types which specify choices by defining `__choices__`, the values are
        passed to the `choices` argument as with `Literal`, but no type inference is
        performed, and the base attribute type will be used as the argument type.

        **Single-value Literals**
        A special case for `Literal` types is when there is only one choice. In this
        case, the argument is added as a `store_const` action, with the value as the
        `const` argument. A further special case is when the choice is `True/False`,
        in which case the action is `store_true`/`store_false` respectively::

            >>> class A(Corgy):
            ...     x: Literal[True]
            ...     y: Literal[False]
            ...     z: Literal[42]

            >>> parser = ArgumentParser()
            >>> A.add_args_to_parser(parser)
            >>> parser.parse_args(["--x"])  # Note that `y` and `z` are absent
            Namespace(x=True)
            >>> parser.parse_args(["--y"])
            Namespace(y=False)
            >>> parser.parse_args(["--z"])
            Namespace(z=42)

        Note: This special case only applies to `Literal` types, and not types which
        define `__choices__`.

        *Corgy*
        Attributes which are themselves `Corgy` types are treated as argument groups.
        Group arguments are added to the command line parser with the group attribute
        name prefixed. Note that groups will ignore any custom flags when computing the
        prefix; elements within the group will use custom flags, but because they are
        prefixed with `--`, they will not be positional.

        Example::

            >>> class G(Corgy):
            ...     x: int = 0
            ...     y: float

            >>> class A(Corgy):
            ...     x: int
            ...     g: G

            >>> parser = ArgumentParser(
            ...     formatter_class=CorgyHelpFormatter,
            ...     add_help=False,
            ...     usage=argparse.SUPPRESS,
            ... )

            >>> A.add_args_to_parser(parser)
            >>> parser.print_help()
            options:
              --x int      (optional)
            <BLANKLINE>
            g:
              --g:x int    (default: 0)
              --g:y float  (optional)

        **Custom parsers**

        Attributes for which a custom parser is defined using `@corgyparser` will
        be added with a custom action that will call the parser. Refer to the
        documentation for `corgyparser` for details.

        **Metavar**

        This function will not explicitly pass a value for the `metavar` argument of
        `ArgumentParser.add_argument`, unless an attribute's type defines `__metavar__`,
        in which case, it will be passed as is. To change the metavar for attributes
        with custom parsers, set the `metavar` argument of `corgyparser`.
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

        required_attrs = getattr(cls, "__required")
        custom_flags = getattr(cls, "__flags")
        custom_parsers = getattr(cls, "__parsers")

        @dataclass
        class _Arg:
            name: str
            required: Optional[bool] = None
            positional: Optional[bool] = None
            dest: Optional[str] = None
            flags: Optional[Sequence[str]] = None
            help: Optional[str] = None
            nargs: Union[int, Literal["+", "*"], None] = None
            action: Optional[Type[argparse.Action]] = None
            choices: Optional[Sequence[Any]] = None
            metavar: Optional[str] = None
            add_type: Optional[Any] = None
            const: Optional[Any] = None

            def get_add_kwargs(self) -> Dict[str, Any]:
                assert self.required is not None
                assert self.positional is not None
                assert self.dest is not None
                kwargs: Dict[str, Any] = {}
                if (not self.positional) and (self.name in custom_flags):
                    kwargs["dest"] = self.dest
                if self.help is not None:
                    kwargs["help"] = self.help
                if self.nargs is not None:
                    kwargs["nargs"] = self.nargs
                if self.action is not None:
                    kwargs["action"] = self.action
                if self.choices is not None:
                    kwargs["choices"] = self.choices

                if self.name in base_defaults:
                    kwargs["default"] = base_defaults[self.name]
                elif self.required and not self.positional:
                    kwargs["required"] = True
                elif not self.positional:
                    kwargs["default"] = argparse.SUPPRESS

                if self.metavar is not None:
                    kwargs["metavar"] = self.metavar
                if self.add_type is not None:
                    kwargs["type"] = self.add_type
                if self.const is not None:
                    kwargs["const"] = self.const

                return kwargs

            def process_optional(self, type_) -> Any:
                if is_optional_type(type_):
                    self.action = OptionalTypeAction
                    return type_.__args__[0]
                return type_

            def process_collection(self, type_) -> Any:
                _col_type = get_concrete_collection_type(type_)
                if _col_type is not None:
                    if (
                        not hasattr(type_, "__args__")
                        or not type_.__args__
                        or isinstance(type_.__args__[0], TypeVar)
                    ):
                        raise TypeError(
                            f"`{self.name}` is a collection, but has no type arguments:"
                            f" use `{type_}[<types>]"
                        )
                    if len(type_.__args__) == 1:
                        self.nargs = "*"
                    elif len(type_.__args__) == 2 and type_.__args__[1] is Ellipsis:
                        # `...` is used to represent non-empty collections, e.g.,
                        # `Sequence[int, ...]`.
                        self.nargs = "+"
                    else:
                        # Ensure single type.
                        if any(_a != type_.__args__[0] for _a in type_.__args__[1:]):
                            raise TypeError(
                                f"`{self.name}` has unsupported type `{type_}`: only"
                                f" single-type collections are supported"
                            )
                        self.nargs = len(type_.__args__)
                    return type_.__args__[0]
                return type_

            def process_choices(self, type_) -> Any:
                _is_literal_type = is_literal_type(type_)
                if _is_literal_type:
                    # Determine if the first choice has `__bases__`, in which case
                    # the first base class is the type for the argument.
                    try:
                        c0_type = type_.__args__[0].__bases__[0]
                    except AttributeError:
                        c0_type = type(type_.__args__[0])
                        f_check_type: Callable[[Any, Any], bool] = isinstance
                    else:
                        f_check_type = issubclass

                    # All choices must be of the same type.
                    if any(not f_check_type(_a, c0_type) for _a in type_.__args__[1:]):
                        raise TypeError(
                            f"choices for `{self.name}` not all of type `{c0_type}`: "
                            f"`{type_.__args__}`"
                        )
                    self.choices = type_.__args__

                    # Convert single choice attributes to `store_*` actions.
                    if (
                        self.choices is not None
                        and len(self.choices) == 1
                        and self.nargs is None
                        and self.action is None
                    ):
                        _choice = self.choices[0]
                        if _choice is True:
                            self.action = _StoreTrueAction
                        elif _choice is False:
                            self.action = _StoreFalseAction
                        else:
                            self.action = _StoreConstAction
                            self.const = _choice
                        self.choices = None
                        return None
                    return c0_type

                if hasattr(type_, "__choices__"):
                    self.choices = type_.__choices__

                return type_

        for var_name, var_type in cls.attrs().items():
            var_arg = _Arg(var_name)
            var_arg.help = getattr(
                cls, var_name
            ).__doc__  # doc is stored in the property
            var_arg.required = (
                var_name not in base_defaults and var_name in required_attrs
            )

            # Determine add flags.
            var_arg.flags = custom_flags.get(
                var_name, [f"--{var_name.replace('_', '-')}"]
            )
            assert var_arg.flags is not None
            if name_prefix:
                var_arg.flags = [
                    f"--{name_prefix.replace('_', '-')}:{flag.lstrip('-')}"
                    for flag in var_arg.flags
                ]
                var_arg.dest = f"{name_prefix}:{var_name}"
            else:
                var_arg.dest = var_name

            # Determine if argument is positional.
            if not any(_flag.startswith("-") for _flag in var_arg.flags):
                # Note: the flags cannot be passed to `add_argument` with `dest` set
                # to `var_name` since `argparse` will raise an error for passing `dest`
                # twice (for positional arguments, `argparse` uses the flag to infer the
                # `dest`).
                var_arg.flags = [var_name]
                var_arg.positional = True
            elif all(_flag.startswith("-") for _flag in var_arg.flags):
                var_arg.positional = False
            else:
                raise TypeError(
                    f"inconsistent positional/optional flags for {var_name}: "
                    f"{var_arg.flags}"
                )

            ###################################################################
            # Check if the variable has a custom parser.
            if var_name in custom_parsers:
                _var_parser = custom_parsers[var_name]
                _var_base_type = var_type
                # Extract choices if present.
                if is_literal_type(var_type):
                    _var_choices = var_type.__args__
                    try:
                        _var_base_type = _var_choices[0].__bases__[0]
                    except AttributeError:
                        _var_base_type = type(_var_choices[0])
                elif hasattr(var_type, "__choices__"):
                    _var_choices = var_type.__choices__
                else:
                    _var_choices = None

                var_arg.action = partial(
                    CorgyParserAction, _var_parser, _var_choices  # type: ignore
                )
                var_arg.add_type = str
                var_arg.nargs = getattr(_var_parser, "__nargs__", None)
                try:
                    var_arg.metavar = _var_parser.__metavar__
                except AttributeError:
                    try:
                        var_arg.metavar = _var_base_type.__metavar__
                    except AttributeError:
                        pass
                parser.add_argument(*var_arg.flags, **var_arg.get_add_kwargs())
                continue

            ###################################################################
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

                grp_parser: _ActionsContainer
                if flatten_subgrps:
                    grp_parser = base_parser
                else:
                    grp_parser = base_parser.add_argument_group(
                        var_arg.dest, var_arg.help
                    )
                var_type.add_args_to_parser(
                    grp_parser, var_arg.dest, True, grp_defaults
                )
                continue

            ###################################################################
            # Check if the variable is boolean. Boolean variables are converted to
            # `--<var-name>`/`--no-<var-name>` arguments (if not positional).
            if var_type is bool:
                var_arg.add_type = bool
                if not var_arg.positional:
                    var_arg.action = BooleanOptionalAction
                parser.add_argument(*var_arg.flags, **var_arg.get_add_kwargs())
                continue

            ###################################################################
            # Process annotations.
            var_base_type = var_type
            var_base_type = var_arg.process_optional(var_base_type)
            var_base_type = var_arg.process_collection(var_base_type)
            var_base_type = var_arg.process_choices(var_base_type)

            if var_base_type is Self:
                raise TypeError(
                    "'add_args_to_parser' cannot be used with 'Self' type present"
                )

            var_arg.metavar = getattr(var_base_type, "__metavar__", None)
            var_arg.add_type = var_base_type
            parser.add_argument(*var_arg.flags, **var_arg.get_add_kwargs())

    def __init__(self, **args):
        if self.__class__ is Corgy:
            raise TypeError("`Corgy` is an abstract class and cannot be instantiated")

        setattr(self, f"_{self.__class__.__name__.lstrip('_')}__frozen", False)

        cls_attrs = self.attrs()
        cls_defaults = getattr(self, "__defaults")
        for attr_name in cls_attrs:
            if attr_name in args:
                setattr(self, attr_name, args[attr_name])
            elif attr_name in cls_defaults:
                setattr(self, attr_name, cls_defaults[attr_name])
            elif attr_name in getattr(self, "__required"):
                raise ValueError(f"missing required attribute: `{attr_name}`")

        if getattr(self.__class__, "__freeze_after_init"):
            self.freeze()

    def _str(self, f_str: Callable[..., str]) -> str:
        s = f"{self.__class__.__name__}("
        i = 0
        for arg_name in self.attrs():
            try:
                _val_s = f_str(getattr(self, arg_name))
            except AttributeError:
                if f_str is repr:
                    continue
                _val_s = "<unset>"
            if i != 0:
                s = s + ", "
            s = s + f"{arg_name}="
            s = s + _val_s
            i += 1
        s = s + ")"
        return s

    def __repr__(self) -> str:
        return self._str(repr)

    def __str__(self) -> str:
        return self._str(str)

    def __eq__(self, other) -> bool:
        if other is self:
            return True
        if self.__class__ is not other.__class__:
            return False
        for _attr in self.attrs():
            _self_has, _other_has = hasattr(self, _attr), hasattr(other, _attr)
            if _self_has != _other_has:
                # One instance has `_attr` set; the other doesn't.
                return False
            if not _self_has:
                # Both instances don't have `_attr` set.
                continue
            if getattr(self, _attr) != getattr(other, _attr):
                return False
        return True

    @classmethod
    def attrs(cls) -> Dict[str, Type]:
        """Return a dictionary mapping attributes of the class to their types.

        Example::

            >>> class A(Corgy):
            ...     x: Annotated[int, "x"]
            ...     y: Sequence[str]

            >>> A.attrs()
            {'x': <class 'int'>, 'y': typing.Sequence[str]}

        """
        return {
            _attr: getattr(cls, _attr).fget.__annotations__["return"]
            for _attr in cls.__annotations__
        }

    def as_dict(self, recursive: bool = True, flatten: bool = False) -> Dict[str, Any]:
        """Return the object as a dictionary.

        The returned dictionary maps attribute names to their values. Unset attributes
        are omitted, unless they have default values.

        Args:
            recursive: whether to recursively call `as_dict` on attributes which are
                `Corgy` instances. Otherwise, they are returned as is.
            flatten: whether to flatten group arguments into `:` separated strings.
                Only takes effect if `recursive` is `True`.

        Examples::

            >>> class G(Corgy):
            ...     x: int

            >>> g = G(x=1)
            >>> g.as_dict()
            {'x': 1}

            >>> class A(Corgy):
            ...     x: str
            ...     g: G

            >>> a = A(x="one", g=g)
            >>> a.as_dict(recursive=False)
            {'x': 'one', 'g': G(x=1)}
            >>> a.as_dict()
            {'x': 'one', 'g': {'x': 1}}
            >>> a.as_dict(flatten=True)
            {'x': 'one', 'g:x': 1}

        """

        def dictify_corgys(_val):
            _coll_type = get_concrete_collection_type(type(_val))
            if _coll_type is not None:
                _cast_type = _coll_type if _coll_type is not AbstractSequence else list
                return _cast_type(  # pylint: disable=abstract-class-instantiated
                    [dictify_corgys(_val_part) for _val_part in _val]
                )
            if isinstance(_val.__class__, CorgyMeta):
                return _val.as_dict(recursive=True, flatten=flatten)
            return _val

        self_dict = {}
        for attr_name, attr_type in self.attrs().items():
            try:
                attr_val = getattr(self, attr_name)
            except AttributeError:
                continue

            if recursive:
                attr_val = dictify_corgys(attr_val)
                if flatten and (isinstance(attr_type, CorgyMeta) or attr_type is Self):
                    for _k, _v in attr_val.items():
                        _flat_key = f"{attr_name}:{_k}"
                        self_dict[_flat_key] = _v
                    continue

            self_dict[attr_name] = attr_val

        return self_dict

    @classmethod
    def from_dict(cls: Type[_T], d: Mapping[str, Any], try_cast: bool = False) -> _T:
        """Return a new instance of the class using a dictionary.

        This is roughly equivalent to `cls(**d)`, with the main exception being that
        groups can be specified as dictionaries themselves, and will be processed
        recursively.

        Args:
            d: Dictionary to create the instance from.
            try_cast: Whether to try and cast values which don't match attribute types.

        Example::

            >>> class G(Corgy):
            ...     x: int

            >>> class A(Corgy):
            ...     x: str
            ...     g: G

            >>> A.from_dict({"x": "one", "g": G(x=1)})
            A(x='one', g=G(x=1))
            >>> A.from_dict({"x": "one", "g": {"x": 1}})
            A(x='one', g=G(x=1))
            >>> A.from_dict({"x": "one", "g": {"x": "1"}}, try_cast=True)
            A(x='one', g=G(x=1))
            >>> G.from_dict({"x": "1"})
            Traceback (most recent call last):
                ...
            ValueError: error setting `x`: invalid value for type '<class 'int'>': '1'

        Group attributes can also be passed directly in the dictionary by prefixing
        their names with the group name and a colon::

            >>> A.from_dict({"x": "one", "g:x": 1})
            A(x='one', g=G(x=1))

            >>> class B(Corgy):
            ...     x: float
            ...     a: A

            >>> B.from_dict({"x": 1.1, "a:x": "one", "a:g:x": 1})
            B(x=1.1, a=A(x='one', g=G(x=1)))

        """
        main_args_map = {}
        grp_args_map: Dict[str, Any] = defaultdict(dict)
        cls_attrs = cls.attrs()

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
                grp_type = cls_attrs[grp_name]
                if not isinstance(grp_type, CorgyMeta):
                    raise ValueError(f"`{grp_name}` is not a `Corgy` class")
                grp_args_map[grp_name][arg_name_base] = arg_val

            elif hasattr(cls, arg_name):
                arg_type = cls_attrs[arg_name]
                if isinstance(arg_type, CorgyMeta) and isinstance(arg_val, dict):
                    grp_args_map[arg_name] = arg_val
                else:
                    main_args_map[arg_name] = arg_val

        for grp_name, grp_args in grp_args_map.items():
            grp_type = cls_attrs[grp_name]
            main_args_map[grp_name] = grp_type.from_dict(grp_args, try_cast)

        cls_attrs = cls.attrs()
        for arg_name, arg_val in main_args_map.copy().items():
            if arg_name in cls_attrs:
                try:
                    main_args_map[arg_name] = check_val_type(
                        arg_val,
                        cls_attrs[arg_name],
                        try_cast,
                        try_load_corgy_dicts=True,
                        self_type=cls,
                    )
                except ValueError as e:
                    raise ValueError(f"error setting `{arg_name}`: {e}") from None
        return cls(**main_args_map)

    def load_dict(
        self, d: Dict[str, Any], try_cast: bool = False, strict: bool = False
    ) -> None:
        """Load a dictionary into an instance of the class.

        Previous attributes are overwritten. Sub-dictionaries will be parsed
        recursively if the corresponding attribute already exists, else will be parsed
        using `from_dict`. As with `from_dict`, items in the dictionary without
        corresponding attributes are ignored.

        Args:
            d: Dictionary to load.
            try_cast: Whether to try and cast values which don't match attribute types.
            strict: If `True`, attributes with existing values that are not in the
                dictionary will be unset.

        Example::

            >>> class A(Corgy):
            ...     x: int
            ...     y: str
            >>> a = A(x=1)
            >>> _i = id(a)
            >>> a.load_dict({"y": "two"})
            >>> a
            A(x=1, y='two')
            >>> _i == id(a)
            True
            >>> a.load_dict({"y": "three"}, strict=True)
            >>> a
            A(y='three')
            >>> _i == id(a)
            True
            >>> a = A()
            >>> a.load_dict({"x": "1"})
            Traceback (most recent call last):
                ...
            ValueError: error setting `x`: invalid value for type '<class 'int'>': '1'
            >>> a.load_dict({"x": "1"}, try_cast=True)
            >>> a
            A(x=1)

        """
        main_args_map: Dict[str, Any] = defaultdict(dict)
        cls_attrs = self.attrs()

        for arg_name, arg_val in d.items():
            if ":" in arg_name:
                grp_name, arg_name_base = arg_name.split(":", maxsplit=1)
                if grp_name not in cls_attrs:
                    raise ValueError(
                        f"invalid argument `{arg_name}`: "
                        f"`{self.__class__}` has no group named `{grp_name}`"
                    )
                if grp_name in d:
                    raise ValueError(
                        f"conflicting arguments: `{arg_name}` and `{grp_name}`"
                    )
                grp_type = cls_attrs[grp_name]
                if not isinstance(grp_type, CorgyMeta):
                    raise ValueError(f"`{grp_name}` is not a `Corgy` class")
                main_args_map[grp_name][arg_name_base] = arg_val

            elif arg_name in cls_attrs:
                main_args_map[arg_name] = arg_val

        for arg_name, arg_type in cls_attrs.items():
            if arg_name not in main_args_map:
                if strict and hasattr(self, arg_name):
                    delattr(self, arg_name)
                continue

            arg_new_val = main_args_map[arg_name]
            if isinstance(arg_type, CorgyMeta) and isinstance(arg_new_val, dict):
                try:
                    arg_obj = getattr(self, arg_name)
                except AttributeError:
                    setattr(self, arg_name, arg_type.from_dict(arg_new_val))
                else:
                    arg_obj.load_dict(arg_new_val, try_cast, strict)
            else:
                try:
                    arg_new_val = check_val_type(
                        arg_new_val,
                        arg_type,
                        try_cast,
                        try_load_corgy_dicts=True,
                        self_type=type(self),
                    )
                except ValueError as e:
                    raise ValueError(f"error setting `{arg_name}`: {e}") from None
                setattr(self, arg_name, arg_new_val)

    @classmethod
    def parse_from_cmdline(
        cls: Type[_T],
        parser: Optional[ArgumentParser] = None,
        defaults: Optional[Mapping[str, Any]] = None,
        **parser_args,
    ) -> _T:
        """Return an instance of the class parsed from command line arguments.

        Args:
            parser: An instance of `argparse.ArgumentParser` or `None`. If `None`, a new
                instance is created.
            defaults: A dictionary of default values for the attributes, passed to
                `add_args_to_parser`. Refer to the docs for `add_args_to_parser` for
                more details.
            parser_args: Arguments to be passed to `argparse.ArgumentParser()`. Ignored
                if `parser` is not None.

        Raises:
            ArgumentTypeError: Error parsing command line arguments.
        """
        if parser is None:
            if "formatter_class" not in parser_args:
                parser_args["formatter_class"] = CorgyHelpFormatter
            parser = ArgumentParser(**parser_args)
        cls.add_args_to_parser(parser, defaults=defaults)
        args = vars(parser.parse_args())
        return cls.from_dict(args, try_cast=True)

    @classmethod
    def parse_from_toml(
        cls: Type[_T],
        toml_file: IO[bytes],
        defaults: Optional[Mapping[str, Any]] = None,
    ) -> _T:
        """Parse an object of the class from a toml file.

        Args:
            toml_file: A file-like object containing the class attributes in toml.
            defaults: A dictionary of default values, overriding any values specified
                in the class.

        Raises:
            TOMLDecodeError: Error parsing the toml file.

        Example::

            >>> class G(Corgy):
            ...     x: int
            ...     y: Sequence[int]

            >>> class A(Corgy):
            ...     x: str
            ...     g: G

            >>> from io import BytesIO
            >>> f = BytesIO(b'''
            ...     x = 'one'
            ...     [g]
            ...     x = 1
            ...     y = [1, 2, 3]
            ... ''')

            >>> A.parse_from_toml(f)  # doctest: +SKIP
            A(x='one', g=G(x=1, y=[1, 2, 3]))

        """
        tomli = import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")
        toml_data = tomli.load(toml_file)
        if defaults is not None:
            for _k, _v in defaults.items():
                if _k not in toml_data:
                    toml_data[_k] = _v
        _parsers = getattr(cls, "__parsers")
        for _k, _v in toml_data.items():
            if _k in _parsers:
                toml_data[_k] = _parsers[_k](_v)
        return cls.from_dict(toml_data, try_cast=True)

    def freeze(self):
        """Freeze the object, preventing any further changes to attributes.

        Example::

            >>> class A(Corgy):
            ...     x: int
            ...     y: int

            >>> a = A(x=1, y=2)
            >>> a.x = 2
            >>> a.freeze()
            >>> a.x = 3
            Traceback (most recent call last):
                ...
            TypeError: cannot set `x`: object is frozen
            >>> del a.y
            Traceback (most recent call last):
                ...
            TypeError: cannot delete `y`: object is frozen

        """
        setattr(self, f"_{self.__class__.__name__.lstrip('_')}__frozen", True)
