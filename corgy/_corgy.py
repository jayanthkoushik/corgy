import argparse
from collections import defaultdict
from collections.abc import Sequence as AbstractSequence
from contextlib import suppress
from functools import partial
from typing import (
    Any,
    Callable,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from ._helpfmt import CorgyHelpFormatter

# The main interface is the `Corgy` class. `_CorgyMeta` modifies creation of `Corgy`
# (and its subclasses) by converting annotations to properties, and setting up utilities
# for command line parsing. `corgyparser` is a decorator that allows custom parsers to
# be defined for `Corgy` variables.

__all__ = ["Corgy", "corgyparser"]
_T = TypeVar("_T", bound="Corgy")


class _CorgyMeta(type):
    """Metaclass for `Corgy`.

    Modifies class creation by parsing type annotations, and creating properties for
    each annotated variable. Default values and custom parsers are stored in the
    `__defaults` and `__parsers` attributes.
    """

    def __new__(cls, name, bases, namespace, **kwds):
        namespace["__slots__"] = []
        if "__annotations__" not in namespace:
            return super().__new__(cls, name, bases, namespace, **kwds)

        namespace["__defaults"] = {}
        for var_name, var_ano in namespace["__annotations__"].items():
            # Check for name conflicts.
            if f"_{name.lstrip('_')}__{var_name}" in (
                namespace | namespace["__annotations__"]
            ):
                raise TypeError(
                    f"cannot use name `__{var_name}`: internal clash with `{var_name}`"
                )

            # Check if help string is present, i.e.,
            # `<var_name>: Annotated[<var_type>, (<var_help>,...)]`.
            if hasattr(var_ano, "__origin__") and hasattr(var_ano, "__metadata__"):
                var_type = var_ano.__origin__
                var_help = var_ano.__metadata__[0]
                if not isinstance(var_help, str):
                    raise TypeError(
                        f"incorrect help string annotation for variable `{var_name}`: "
                        f"expected str"
                    )
            else:
                # `<var_name>: <var_type>`.
                var_type = var_ano
                var_help = None
            namespace["__annotations__"][var_name] = var_type

            # Add default value to dedicated dict.
            with suppress(KeyError):
                namespace["__defaults"][var_name] = namespace[var_name]

            # Create `<var_name>` property.
            namespace[var_name] = cls._create_var_property(
                name, var_name, var_type, var_help
            )
            namespace["__slots__"].append(f"__{var_name}")

        # Store custom parsers in a dict.
        namespace["__parsers"] = {}
        for _, v in namespace.items():
            if not isinstance(v, _CorgyParser):
                continue
            var_name = v.var_name
            if (var_name in namespace) and isinstance(namespace[var_name], property):
                namespace["__parsers"][var_name] = v.fparse
            else:
                raise TypeError(f"invalid target for corgyparser: {v.var_name}")

        return super().__new__(cls, name, bases, namespace, **kwds)

    @staticmethod
    def _create_var_property(cls_name, var_name, var_type, var_doc):
        # Properties are stored in private instance variables prefixed with `__`, and
        # must be accessed as `_<cls>__<var_name>`.
        def var_fget(self) -> var_type:
            with suppress(AttributeError):
                return getattr(self, f"_{cls_name.lstrip('_')}__{var_name}")
            with suppress(KeyError):
                return getattr(self, "__defaults")[var_name]
            raise AttributeError(f"no value available for attribute `{var_name}`")

        def var_fset(self, val: var_type):
            setattr(self, f"_{cls_name.lstrip('_')}__{var_name}", val)

        return property(var_fget, var_fset, doc=var_doc)


class Corgy(metaclass=_CorgyMeta):
    """Base class for collections of variables.

    To create a command line interface, subclass `Corgy`, and declare your arguments
    using type annotations::

        class A(Corgy):
            x: int
            y: float

    At runtime, class `A` will have `x`, and `y` as properties, so that the class can be
    used similar to Python dataclasses::

        a = A()
        a.x = 1
        a.y = a.x + 1.1

    For command line parsing, `x` and `y` are added to an `ArgumentParser` object with
    the appropriate arguments passed to `ArgumentParser.add_argument`. This is roughly
    equivalent to::

        parser = ArgumentParser()
        parser.add_argument("--x", type=int, required=True)
        parser.add_argument("--y", type=float, required=True)

    `Corgy` does not support positional arguments. All arguments are converted to
    optional arguments, and prefixed with `--`.

    `Corgy` recognizes a number of special annotations, which are used to control how
    the argument is parsed.

    **Annotated**:
    `typing.Annotated` can be used to add a help message::

        x: Annotated[int, "help for x"]

    `Annotated` can accept multiple arguments, but only the first two are used by
    `Corgy`. The first argument is the type, and the second is the help message.
    `Annotated` should always be the outermost annotation; other special annotations
    should be part of the type.

    **Optional**:
    `typing.Optional` can be used to mark an argument as optional::

        x: Optional[int]

    Another way to mark an argument as optional is to provide a default value::

        x: int = 0

    Default values can be used in conjunction with `Optional`::

        x: Optional[int] = 0

    Note that the last two examples are not equivalent, since the type of `x` is
    `Optional[int]` in the last example, so it is allowed to be `None`.

    When parsing from the command line, arguments which are not marked as optional
    (because they are not marked with `Optional`, and don't have a default value) will
    be required.

    Note:
        Default values are not type checked, and can be arbitrary objects.

    **Sequence**
    `collections.abc.Sequence` can be used to specify that an argument accepts multiple
    space-separated values. `typing.Sequence` can also be used, but is not recommended
    as it is deprecated since Python 3.9.

    There are a few different ways to use `Sequence`, each resulting in different
    conditions for the parser. The simplest case is a plain sequence::

        x: Sequence[int]

    This represents a (possibly empty) sequence, and corresponds to the following call
    to `ArgumentParser.add_argument`::

        parser.add_argument("--x", type=int, nargs="*", required=True)

    Note that since the argument is required, parsing an empty list will still require
    `--x` in the command line. After parsing, `x` will be a `list`. To denote an
    optional sequence, use `Optional[Sequence[...]]`.

    To specify that a sequence must be non-empty, use::

        x: Sequence[int, ...]

    This will result in `nargs` being set to `+` in the call to
    `ArgumentParser.add_argument`. Using this syntax **requires**
    `collections.abc.Sequence`, since `typing.Sequence` does not accept `...` as an
    argument.

    Finally, you can specify a fixed length sequence::

        x: Sequence[int, int, int]

    This amounts to `nargs=3`. All types in the sequence must be the same. So,
    `Sequence[int, str, int]` will result in a `TypeError`.

    **Literal**
    `typing.Literal` can be used to specify that an argument takes one of a fixed set of
    values::

        x: Literal[0, 1, 2]

    The provided values are passed to the `choices` argument of
    `ArgumentParser.add_argument`. All values must be of the same type, which will be
    inferred from the type of the first value.

    `Literal` itself can be used as a type, for instance inside a `Sequence`::

        x: Sequence[Literal[0, 1, 2], Literal[0, 1, 2]]

    This is a sequence of length 2, where each element is either 0, 1, or 2.

    **Bool**
    `bool` types (when not in a sequence) are converted to
    `argparse.BooleanOptionalAction`::

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

    Finally, `Corgy` classes can themselves be used as a type, to represent a group of
    arguments::

        class A(Corgy):
            x: int
            y: float

        class B(Corgy):
            x: int
            grp: Annotated[A, "a group"]

    Group arguments are added to the command line parser with the group argument name
    prefixed. In the above example, parsing using `B` would result in the arguments
    `--x`, `--grp:x`, and `--grp:y`. `grp:x` and `grp:y` will be converted to an
    instance of `A`, and set as the `grp` property of `B`.
    """

    @classmethod
    def add_args_to_parser(cls, parser: argparse.ArgumentParser, name_prefix: str = ""):
        """Add arguments for this class to the given parser.

        Args:
            parser: `argparse.ArgumentParser` instance.
            name_prefix: Prefix for argument names (default: empty string). Arguments
                will be named `--<name-prefix>:<var-name>`.
        """
        for (var_name, var_type) in getattr(cls, "__annotations__").items():
            var_dashed_name = var_name.replace("_", "-")
            if name_prefix:
                var_dashed_name = name_prefix.replace("_", "-") + ":" + var_dashed_name
            var_help = getattr(cls, var_name).__doc__  # doc is stored in the property

            # Check if the variable is also `Corgy` type.
            if type(var_type) is type(cls):
                # Create an argument group using `<var_type>`.
                grp_parser = parser.add_argument_group(var_dashed_name, var_help)
                var_type.add_args_to_parser(grp_parser, var_dashed_name)
                continue

            # Check if the variable is optional. `<var_name>: Optional[<var_type>]` is
            # equivalent to `<var_name>: Union[<var_type>, None]`.
            if (
                hasattr(var_type, "__origin__")
                and var_type.__origin__ is Union
                and len(var_type.__args__) == 2
                and var_type.__args__[1] is type(None)
            ):
                var_base_type = var_type.__args__[0]
                var_required = False
            else:
                var_base_type = var_type
                var_required = var_name not in getattr(cls, "__defaults")

            # Check if the variable has a custom parser.
            if var_name in (_parsers := getattr(cls, "__parsers")):
                var_fparse = _parsers[var_name]
                _kwargs: dict[str, Any] = {}
                if var_help is not None:
                    _kwargs["help"] = var_help
                if var_name in (_defaults := getattr(cls, "__defaults")):
                    _kwargs["default"] = _defaults[var_name]
                if var_required:
                    _kwargs["required"] = True
                parser.add_argument(f"--{var_dashed_name}", type=var_fparse, **_kwargs)
                continue

            # Check if the variable is a sequence.
            var_nargs: Union[int, Literal["+", "*"], None]
            if hasattr(var_base_type, "__origin__") and (
                var_base_type.__origin__ is Sequence
                or var_base_type.__origin__ is AbstractSequence
            ):
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
                        _a is not var_base_type.__args__[0]
                        for _a in var_base_type.__args__[1:]
                    ):
                        raise TypeError(
                            f"`{var_name}` has unsupported type `{var_base_type}`: only"
                            f"single-type sequences are supported"
                        )
                    var_nargs = len(var_base_type.__args__)
                var_base_type = var_base_type.__args__[0]
            else:
                var_nargs = None

            # Check if the variable has choices i.e. `Literal[<x>, <y>, ...]`.
            if (
                hasattr(var_base_type, "__origin__")
                and var_base_type.__origin__ is Literal
            ):
                # All choices must be of the same type.
                if any(
                    type(_a) is not type(var_base_type.__args__[0])
                    for _a in var_base_type.__args__[1:]
                ):
                    raise TypeError(
                        f"choices for `{var_name}` not same type: "
                        f"`{var_base_type.__args__}`"
                    )
                var_choices = var_base_type.__args__
                var_base_type = type(var_base_type.__args__[0])
            else:
                var_choices = None

            # Check if the variable is boolean. Boolean variables are converted to
            # `--<var-name>`/`--no-<var-name>` arguments.
            var_action: Optional[Type[argparse.Action]]
            if var_base_type is bool and var_nargs is None:
                var_action = argparse.BooleanOptionalAction
            else:
                var_action = None

            # Add the variable to the parser.
            _kwargs = {}
            if var_help is not None:
                _kwargs["help"] = var_help
            if var_nargs is not None:
                _kwargs["nargs"] = var_nargs
            if var_action is not None:
                _kwargs["action"] = var_action
            if var_choices is not None:
                _kwargs["choices"] = var_choices
            if var_name in (_defaults := getattr(cls, "__defaults")):
                _kwargs["default"] = _defaults[var_name]
            if var_required:
                _kwargs["required"] = True
            parser.add_argument(f"--{var_dashed_name}", type=var_base_type, **_kwargs)

    @classmethod
    def _new_with_args(cls: type[_T], **args) -> _T:
        """Create a new instance of the class using the given arguments.

        Arguments with `:` in their name are passed to group class constructors.
        """
        obj = object.__new__(cls)
        grp_args_map: dict[str, Any] = defaultdict(dict)

        for arg_name, arg_val in args.items():
            if ":" in arg_name:
                grp_name, arg_name = arg_name.split(":", maxsplit=1)
                grp_args_map[grp_name][arg_name] = arg_val
            else:
                setattr(obj, arg_name, arg_val)

        for grp_name, grp_args in grp_args_map.items():
            grp_type = getattr(cls, grp_name).fget.__annotations__["return"]
            grp_obj = grp_type._new_with_args(**grp_args)
            setattr(obj, grp_name, grp_obj)

        return obj

    def __str__(self) -> str:
        s = f"{self.__class__.__name__}("
        for i, arg_name in enumerate(getattr(self.__class__, "__annotations__")):
            if i != 0:
                s = s + ", "
            s = s + f"{arg_name}="
            try:
                _val_s = repr(getattr(self, arg_name))
            except AttributeError:
                _val_s = "<unset>"
            s = s + _val_s
        s = s + ")"
        return s

    @classmethod
    def parse_from_cmdline(
        cls: type[_T], parser: Optional[argparse.ArgumentParser] = None, **parser_args
    ) -> _T:
        """Parse an object of the class from command line arguments.

        Args:
            parser: An instance of `argparse.ArgumentParser` or `None`. If `None`, a new
                instance is created.
            parser_args: Arguments to be passed to `argparse.ArgumentParser()`. Ignored
                if `parser` is not None.
        """
        if parser is None:
            if "formatter_class" not in parser_args:
                parser_args["formatter_class"] = CorgyHelpFormatter
            parser = argparse.ArgumentParser(**parser_args)
        cls.add_args_to_parser(parser)
        args = vars(parser.parse_args())
        return cls._new_with_args(**args)


class _CorgyParser(NamedTuple):
    """Class to represent custom parsers.

    This class is returned by the `@corgyparser` decorator, and is used by `Corgy` to
    keep track of parsers.
    """

    var_name: str
    fparse: Callable[[str], Any]


def corgyparser(var_name: str) -> Callable[[Callable[[str], Any]], _CorgyParser]:
    """Decorate a function as a custom parser for a variable.

    To use a custom function for parsing an argument with `Corgy`, use this decorator.

    Args:
        var_name: The argument associated with the decorated parser.

    Example::

        class A(Corgy):
            time: tuple[int, int, int]
            @corgyparser("time")
            def parse_time(s):
                return tuple(map(int, s.split(":")))
    """
    if not isinstance(var_name, str):
        raise TypeError(
            "corgyparser should be passed the name of an argument: decorate using"
            "@corgyparser(<argument>)"
        )

    def wrapper(var_name: str, fparse: Callable[[str], Any]):
        return _CorgyParser(var_name, fparse)

    return partial(wrapper, var_name)
