from __future__ import annotations

import sys
from argparse import Action, ArgumentError
from functools import partial
from typing import Any, Callable, Collection, List, NamedTuple, Optional, Union

if sys.version_info >= (3, 9):
    from typing import Literal
else:
    from typing_extensions import Literal

__all__ = ("corgyparser",)


class CorgyParser(NamedTuple):
    """Class to represent custom parsers.

    This class is returned by the `@corgyparser` decorator, and is used by `Corgy` to
    keep track of parsers.
    """

    var_names: List[str]
    fparse: Callable[[str], Any]
    nargs: Union[None, Literal["*", "+"], int]

    def __call__(self, s):
        return self.fparse(s)


class CorgyParserAction(Action):
    def __init__(
        self, corgy_parser: CorgyParser, choices: Optional[Collection], *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._corgy_parser = corgy_parser
        self._choices = choices

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            val = self._corgy_parser(values)
            if self._choices is not None and val not in self._choices:
                raise ValueError(
                    f"invalid choice: {val} (choose from "
                    f"{', '.join(map(str, self._choices))})"
                )
            setattr(namespace, self.dest, val)
        except ValueError as e:
            raise ArgumentError(self, str(e)) from None


def corgyparser(
    *var_names: str,
    metavar: Optional[str] = None,
    nargs: Union[None, Literal["*", "+"], int] = None,
) -> Callable[[Union[Callable[[str], Any], CorgyParser]], CorgyParser]:
    """Decorate a function as a custom parser for one or more attributes.

    To use a custom function for parsing a `Corgy` attribute, use this decorator.
    Parsing functions must be static, and should only accept a single argument.
    Decorating the function with `@staticmethod` is optional, but prevents type errors.
    `@corgyparser` must be the final decorator in the decorator chain.

    Args:
        var_names: The attributes associated with the decorated parser.
        metavar: Keyword only argument to set the metavar when adding the associated
            attribute(s) to an `ArgumentParser` instance.
        nargs: Keyword only argument to set the number of arguments to be used for the
            associated attribute(s). Must be `None`, `'*'`, `'+'`, or a positive number.
            This value is passed as the `nargs` argument to
            `ArgumentParser.add_argument`, and controls the number of arguments that
            will be read from the command line, and passed to the parsing function.
            For all values other than `None`, the parsing function will receive a list
            of strings.

    Example::

        >>> import argparse
        >>> from argparse import ArgumentParser
        >>> from typing import Tuple
        >>> from corgy import Corgy, CorgyHelpFormatter, corgyparser

        >>> class A(Corgy):
        ...     time: Tuple[int, int, int]
        ...     @corgyparser("time", metavar="int:int:int")
        ...     @staticmethod
        ...     def parse_time(s):
        ...         return tuple(map(int, s.split(":")))

        >>> parser = ArgumentParser(
        ...     formatter_class=CorgyHelpFormatter,
        ...     add_help=False,
        ...     usage=argparse.SUPPRESS,
        ... )

        >>> A.add_args_to_parser(parser)
        >>> parser.parse_args(["--time", "1:2:3"])
        Namespace(time=(1, 2, 3))

    Multiple arguments can be passed to the decorator, and will all be associated with
    the same parser::

        >>> class A(Corgy):
        ...     x: int
        ...     y: int
        ...     @corgyparser("x", "y")
        ...     @staticmethod
        ...     def parse_x_y(s):
        ...         return int(s)

    The `@corgyparser` decorator can also be chained to use the same parser for multiple
    arguments::

        >>> class A(Corgy):
        ...     x: int
        ...     y: int
        ...     @corgyparser("x")
        ...     @corgyparser("y")
        ...     @staticmethod
        ...     def parse_x_y(s):
        ...         return int(s)

    Note: when chaining, the outer-most non-`None` value of `metavar` will be used.

    Custom parsers can control the number of arguments they receive, independent of the
    argument type::

        >>> class A(Corgy):
        ...     x: int
        ...     @corgyparser("x", nargs=3)
        ...     @staticmethod
        ...     def parse_x(s):
        ...         # `s` will be a list of 3 strings.
        ...         return sum(map(int, s))

        >>> parser = ArgumentParser(
        ...     formatter_class=CorgyHelpFormatter,
        ...     add_help=False,
        ...     usage=argparse.SUPPRESS,
        ... )

        >>> A.add_args_to_parser(parser)
        >>> parser.parse_args(["--x", "1", "2", "3"])
        Namespace(x=6)

    When chaining, `nargs` must be the same for all decorators, otherwise `TypeError` is
    raised.
    """
    if not all(isinstance(_var_name, str) for _var_name in var_names):
        raise TypeError(
            "corgyparser should be passed the name of arguments: decorate using"
            "@corgyparser(<argument(s)>)"
        )

    def wrapper(var_names, metavar, fparse):
        if isinstance(fparse, CorgyParser):
            if nargs != fparse.nargs:
                raise TypeError(
                    "all `corgyparser` decorations of a funciton must have same `nargs`"
                )
            corgy_parser = fparse
            corgy_parser.var_names.extend(var_names)
        else:
            if isinstance(fparse, staticmethod):
                fparse = fparse.__func__
            if not callable(fparse):
                raise TypeError("corgyparser can only decorate static functions")
            corgy_parser = CorgyParser(list(var_names), fparse, nargs)

        if metavar is not None:
            setattr(corgy_parser.fparse, "__metavar__", metavar)
        if nargs is not None:
            setattr(corgy_parser.fparse, "__nargs__", nargs)
        return corgy_parser

    return partial(wrapper, var_names, metavar)
