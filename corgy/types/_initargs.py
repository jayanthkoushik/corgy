from __future__ import annotations

import inspect
import sys
from typing import Generic, NoReturn, Type, TypeVar

from corgy import Corgy

__all__ = ("InitArgs",)
_T = TypeVar("_T")


class InitArgs(Corgy, Generic[_T], corgy_required_by_default=True):
    """Corgy wrapper around arguments of a class's `__init__`.

    Example::

        >>> import argparse
        >>> from argparse import ArgumentParser
        >>> from typing import Sequence
        >>> from corgy import CorgyHelpFormatter
        >>> from corgy.types import InitArgs

        >>> class Foo:
        ...     def __init__(
        ...         self,
        ...         a: int,
        ...         b: Sequence[str],
        ...         c: float = 0.0,
        ...     ):
        ...         ...

        >>> FooInitArgs = InitArgs[Foo]
        >>> parser = ArgumentParser(
        ...     formatter_class=CorgyHelpFormatter,
        ...     add_help=False,
        ...     usage=argparse.SUPPRESS,
        ... )
        >>> FooInitArgs.add_args_to_parser(parser)
        >>> parser.print_help()
        options:
          --a int        (required)
          --b [str ...]  (required)
          --c float      (default: 0.0)

        >>> args = parser.parse_args(["--a", "1", "--b", "one", "two"])
        >>> foo = Foo(args.a, args.b, args.c)

    This is a generic class, and on using the `InitArgs[Cls]` syntax, a concrete
    `Corgy` class is created, which has attributes corresponding to the arguments of
    `Cls.__init__`, with types inferred from annotations. The returned class can be used
    as any other `Corgy` class, including as a type annotation within another `Corgy`
    class.

    All arguments of the `__init__` method must be annotated, following the same rules
    as for other `Corgy` classes. Positional only arguments are not supported, since
    they are not associated with an argument name. `TypeError` is raised if either of
    these conditions is not met.
    """

    __slots__ = ()

    def __class_getitem__(cls, item: Type[_T]) -> Type[InitArgs[_T]]:
        try:
            is_generic = issubclass(item, Generic)  # type: ignore
        except TypeError as e:
            raise TypeError(f"could not perform class test on `{item}`: {e}") from None
        if is_generic:
            raise TypeError(f"{cls.__name__} cannot be used with generic classes")
        item_sig = inspect.signature(item)
        item_annotations, item_defaults = {}, {}
        for param_name, param in item_sig.parameters.items():
            if param.annotation is inspect.Parameter.empty:
                raise TypeError(
                    f"`{item}` is missing annotation for parameter `{param_name}`"
                )

            if param.kind is inspect.Parameter.POSITIONAL_ONLY:
                raise TypeError(
                    f"positional-only paramter `{param_name}` is incompatible with "
                    f"`{cls.__name__}`"
                )

            item_annotations[param_name] = param.annotation
            if param.default is not inspect.Parameter.empty:
                item_defaults[param_name] = param.default

        def new_cls_getitem(newcls, _item: Type[_T]) -> NoReturn:
            raise TypeError(
                f"cannot further sub-script `{newcls.__name__}[{_item.__name__}]`"
            )

        ret_type = type(
            f"{cls.__name__}[{item.__name__}]",
            (cls,),
            {
                "__annotations__": item_annotations,
                "__module__": item.__module__,
                "__class_getitem__": new_cls_getitem,
                **item_defaults,
            },
        )
        sys.modules[ret_type.__module__].__dict__[ret_type.__name__] = ret_type
        return ret_type
