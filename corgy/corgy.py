import argparse
from collections import defaultdict
from collections.abc import Sequence as AbstractSequence
from contextlib import suppress
from typing import Any, Literal, Optional, Sequence, Type, TypeVar, Union

__all__ = ["Corgy"]
_T = TypeVar("_T", bound="Corgy")


class _CorgyMeta(type):
    """Metaclass for Corgy.

    Modifies class creation by parsing annotations, and creating variable properties.
    """

    def __new__(cls, name, bases, namespace, **kwds):
        namespace["__slots__"] = []
        if "__annotations__" not in namespace:
            return super().__new__(cls, name, bases, namespace, **kwds)

        namespace["__defaults"] = dict()
        for var_name, var_ano in namespace["__annotations__"].items():
            if f"_{name.lstrip('_')}__{var_name}" in (
                namespace | namespace["__annotations__"]
            ):
                raise TypeError(
                    f"cannot use name '__{var_name}': internal clash with '{var_name}'"
                )

            # Check if help string is present
            #   i.e. var_name: Annotated[var_type, (var_help,...)]
            if hasattr(var_ano, "__origin__") and hasattr(var_ano, "__metadata__"):
                var_type = var_ano.__origin__
                var_help = var_ano.__metadata__[0]
                if not isinstance(var_help, str):
                    raise TypeError(
                        f"incorrect help string annotation for variable '{var_name}': "
                        f"expected str"
                    )
            else:
                # var_name: var_type
                var_type = var_ano
                var_help = None
            namespace["__annotations__"][var_name] = var_type

            # Add default value to dedicated dict
            with suppress(KeyError):
                namespace["__defaults"][var_name] = namespace[var_name]

            # Create 'var' property
            namespace[var_name] = cls._create_var_property(
                name, var_name, var_type, var_help
            )
            namespace["__slots__"].append(f"__{var_name}")

        return super().__new__(cls, name, bases, namespace, **kwds)

    @staticmethod
    def _create_var_property(cls_name, var_name, var_type, var_doc):
        # Properties are stored in private instance variables prefixed with "__",
        #   and must be accessed as _cls__var_name
        def var_fget(self) -> var_type:
            with suppress(AttributeError):
                return getattr(self, f"_{cls_name.lstrip('_')}__{var_name}")
            with suppress(KeyError):
                return getattr(self, "__defaults")[var_name]
            raise AttributeError(f"no value available for attribute '{var_name}'")

        def var_fset(self, val: var_type):
            setattr(self, f"_{cls_name.lstrip('_')}__{var_name}", val)

        return property(var_fget, var_fset, doc=var_doc)


class Corgy(metaclass=_CorgyMeta):
    """Base class for collections of arguments.

    User-defined classes inheriting from Corgy should declare their
    arguments as type annotations. For example,

    class A(Corgy):
        x: int
        y: str
        z: Annotated[str, "this is z"]

    At runtime, class 'A' will have 'x', 'y', and 'z' as properties,
    and will provide methods to parse them from command line arguments.
    """

    @classmethod
    def add_args_to_parser(cls, parser: argparse.ArgumentParser, name_prefix: str = ""):
        for (
            var_name,
            var_type,
        ) in getattr(cls, "__annotations__").items():
            var_dashed_name = var_name.replace("_", "-")
            if name_prefix:
                var_dashed_name = name_prefix.replace("_", "-") + ":" + var_dashed_name
            var_help = getattr(cls, var_name).__doc__  # doc is stored in the property

            # Check if 'var_name' is also Corgy type
            if type(var_type) is type(cls):
                # Create an argument group using 'var_type'
                grp_parser = parser.add_argument_group(var_dashed_name, var_help)
                var_type.add_args_to_parser(grp_parser, var_dashed_name)
                continue

            # Check if 'var_name' is optional
            #   var_name: Optional[var_type] is equivalent to
            #   var_name: Union[var_type, None]
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

            # Check if 'var_name' is a sequence
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
                    # '...' is used to represent non-empty collections
                    #   e.g. Sequence[int, ...]
                    var_nargs = "+"
                else:
                    # Ensure single type
                    if any(
                        _a is not var_base_type.__args__[0]
                        for _a in var_base_type.__args__[1:]
                    ):
                        raise TypeError(
                            f"'{var_name}' has unsupported type '{var_base_type}': "
                            f"only single-type sequences are supported"
                        )
                    var_nargs = len(var_base_type.__args__)
                var_base_type = var_base_type.__args__[0]
            else:
                var_nargs = None

            # Check if 'var_name' has choices
            #   i.e. var_name: Literal[x, y, ...]
            if (
                hasattr(var_base_type, "__origin__")
                and var_base_type.__origin__ is Literal
            ):
                # All choices must be of the same type
                if any(
                    type(_a) is not type(var_base_type.__args__[0])
                    for _a in var_base_type.__args__[1:]
                ):
                    raise TypeError(
                        f"choices for '{var_name}' not same type: "
                        f"'{var_base_type.__args__}'"
                    )
                var_choices = var_base_type.__args__
                var_base_type = type(var_base_type.__args__[0])
            else:
                var_choices = None

            if type(var_base_type) is not type:  # pylint: disable=unidiomatic-typecheck
                raise TypeError(f"{var_base_type} is not a valid type")

            # Check if 'var_name' is boolean
            # Boolean variables are converted to '--var-name'/'--no-var-name' arguments
            var_action: Optional[Type[argparse.Action]]
            if var_base_type is bool and var_nargs is None:
                var_action = argparse.BooleanOptionalAction
            else:
                var_action = None

            # Add 'var_name' to parser
            _kwargs: dict[str, Any] = {}
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
            parser.add_argument(
                f"--{var_dashed_name}",
                type=var_base_type,
                **_kwargs,
            )

    @classmethod
    def _new_with_args(cls: type[_T], **args) -> _T:
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
    def parse_from_cmdline(cls: type[_T], parser=None, **parser_args) -> _T:
        if parser is None:
            parser = argparse.ArgumentParser(**parser_args)
        cls.add_args_to_parser(parser)
        args = vars(parser.parse_args())
        return cls._new_with_args(**args)
