from functools import partial
from typing import Callable, List, NamedTuple, Union

__all__ = ("corgychecker",)


class CorgyChecker(NamedTuple):
    """Class to represent custom checkers.

    This class is returned by the `@corgychecker` decorator, and is used by `Corgy` to
    keep track of checkers.
    """

    var_names: List[str]
    fcheck: Callable

    def __call__(self, val):
        return self.fcheck(val)


def corgychecker(
    *var_names: str,
) -> Callable[[Union[Callable, CorgyChecker]], CorgyChecker]:
    """Decorate a function as a custom checker for one or more attributes.

    To use a custom function for checking the value of a `Corgy` attribute, use this
    decorator. Checking functions must be static, and should only accept a single
    argument, the value to be checked. They should raise `ValueError` to indicate value
    mismatch. Decorating the function with `@staticmethod` is optional, but prevents
    type errors. `@corgychecker` must be the final decorator in the decorator chain.

    Custom checkers are called _after_ type checking, so the values passed to them will
    be of type corresponding to one of the assigned attributes.

    Args:
        var_names: The attributes associated with the decorated checker.

    Example::

        >>> from corgy import Corgy, corgychecker

        >>> class A(Corgy):
        ...     x: int
        ...     @corgychecker("x")
        ...     @staticmethod
        ...     def check_x(val):
        ...         if val % 2:
        ...             raise ValueError(f"'{val}' is not even")

        >>> a = A()
        >>> a.x = 2
        >>> a.x = 3
        Traceback (most recent call last):
           ...
        ValueError: error setting `x`: '3' is not even

    Multiple attributes can use the same checker, either by chaining `corgychecker`, or
    by passing all attribute names directly::

        >>> from typing import Sequence

        >>> class A(Corgy):
        ...     x: int
        ...     y: float
        ...     z: str
        ...     w: Sequence[int]
        ...     @corgychecker("x")
        ...     @corgychecker("y")
        ...     def check_num(val):
        ...         if val < 0:
        ...             raise ValueError("should be non-negative")
        ...     @corgychecker("z", "w")
        ...     def check_seq(val):
        ...         if len(val) > 10:
        ...             raise ValueError("too long")

    """
    if not all(isinstance(_var_name, str) for _var_name in var_names):
        raise TypeError(
            "corgychecker should be passed the name of arguments: decorate using"
            "@corgychecker(<argument(s)>)"
        )

    def wrapper(var_names, fcheck):
        if isinstance(fcheck, CorgyChecker):
            corgy_checker = fcheck
            corgy_checker.var_names.extend(var_names)
        else:
            if isinstance(fcheck, staticmethod):
                fcheck = fcheck.__func__
            if not callable(fcheck):
                raise TypeError("corgychecker can only decorate static functions")
            corgy_checker = CorgyChecker(list(var_names), fcheck)
        return corgy_checker

    return partial(wrapper, var_names)
