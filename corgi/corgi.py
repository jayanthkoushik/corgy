import argparse
from collections.abc import Collection, Mapping
from contextlib import suppress
from typing import Any, Literal, Optional, Type, Union


class _CorgiMeta(type):
    """Metaclass for Corgi.

    Modifies class creation by parsing annotations, and creating variable properties.
    """

    def __new__(cls, name, bases, namespace, **kwds):
        if "__annotations__" not in namespace:
            return super().__new__(cls, name, bases, namespace, **kwds)

        namespace["_defaults"] = dict()
        for var_name, var_ano in namespace["__annotations__"].items():
            # Check if help string is present
            #   i.e. var_name: Annotated[var_type, (var_help,...)]
            if hasattr(var_ano, "__metadata__"):
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
                namespace["_defaults"][var_name] = namespace[var_name]

            # Create 'var' property
            namespace[var_name] = cls._create_var_property(var_name, var_type, var_help)

        return super().__new__(cls, name, bases, namespace, **kwds)

    @staticmethod
    def _create_var_property(var_name, var_type, var_doc):
        # Properties are stored in private variables prefixed with "_"
        def _var_fget(self) -> var_type:
            return getattr(self, f"_{var_name}")

        def _var_fset(self, val: var_type):
            setattr(self, f"_{var_name}", val)

        return property(_var_fget, _var_fset, doc=var_doc)


class Corgi(metaclass=_CorgiMeta):
    """Base class for collections of arguments.

    User-defined classes inheriting from Corgi should declare their
    arguments as type annotations. For example,

    class A(Corgi):
        x: int
        y: str
        z: Annotated[str, "this is z"]

    At runtime, class 'A' will have 'x', 'y', and 'z' as properties,
    and will provide methods to parse them from command line arguments.
    """

    _defaults: dict[str, Any]

    def __getattr__(self, name):
        # Hook to return default value when property access fails
        with suppress(KeyError):
            return self._defaults[name]
        raise AttributeError

    @classmethod
    def add_args_to_parser(cls, parser: argparse.ArgumentParser):
        for var_name, var_type in cls.__annotations__.items():
            var_dashed_name = var_name.replace("_", "-")
            var_help = getattr(cls, var_name).__doc__  # doc is stored in the property

            # Check if 'var_name' is also CorgiType
            if type(var_type) is type(cls):
                # Create an argument group using 'var_type'
                grp_parser = parser.add_argument_group(var_dashed_name, var_help)
                var_type._add_args_to_parser(grp_parser)
                continue

            # Check if 'var_name' is optional
            #   var_name: Optional[var_type] is equivalent to
            #   var_name: Union[var_type, None]
            if (
                hasattr(var_type, "__origin__")
                and var_type.__origin__ is Union
                and var_type.__args__[1] is type(None)
            ):
                var_base_type = var_type.__args__[0]
                var_required = False
            else:
                var_base_type = var_type
                var_required = var_name not in cls._defaults

            # Check if 'var_name' is a collection
            # Only non-mapping single-type collections are supported
            var_nargs: Optional[Union[int, Literal["+", "*"]]]
            if (
                hasattr(var_base_type, "__origin__")
                and isinstance(var_base_type.__origin__, type)
                and issubclass(var_base_type.__origin__, Collection)
                and not issubclass(var_base_type.__origin__, Mapping)
            ):
                if len(var_base_type.__args__) == 1:
                    var_nargs = "*"
                elif (
                    len(var_base_type.__args__) == 2
                    and var_base_type.__args__[1] is Ellipsis
                ):
                    # '...' is used to represent non-empty lists
                    #   e.g. list[int, ...]
                    var_nargs = "+"
                else:
                    # Ensure single type
                    if any(
                        _a is not var_base_type.__args__[0]
                        for _a in var_base_type.__args__[1:]
                    ):
                        raise TypeError(
                            f"'{var_name}' has unsupported type '{var_base_type}': "
                            f"only single-type collections are supported"
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
                    for _a in var_base_type.__args__
                ):
                    raise TypeError(
                        f"choices for '{var_name}' not same type: "
                        f"'{var_base_type.__args__}'"
                    )
                var_choices = var_base_type.__args__
                var_base_type = type(var_base_type.__args__[0])
            else:
                var_choices = None

            # Check if 'var_name' is boolean
            # Boolean variables are converted to '--var-name'/'--no-var-name' arguments
            var_action: Optional[Type[argparse.Action]]
            if var_base_type is bool:
                var_action = argparse.BooleanOptionalAction
                var_required = False
            else:
                var_action = None

            # Add 'var_name' to parser
            # 'add_argument' does not always accept all args
            #    these are passed if needed through '_kwargs'
            _kwargs: Any = {}
            if var_help is not None:
                _kwargs["help"] = var_help
            if var_nargs is not None:
                _kwargs["nargs"] = var_nargs
            if var_action is not None:
                _kwargs["action"] = var_action
            if var_choices is not None:
                _kwargs["choices"] = var_choices
            if var_name in cls._defaults:
                _kwargs["default"] = cls._defaults[var_name]
            if var_required:
                _kwargs["required"] = True
            parser.add_argument(
                f"--{var_dashed_name}",
                type=var_base_type,
                **_kwargs,
            )

    @classmethod
    def parse_from_cmdline(cls, parser=None, **parser_args):
        if parser is None:
            parser = argparse.ArgumentParser(**parser_args)
        cls.add_args_to_parser(parser)
        args = parser.parse_args()
        c = cls()
        for k, v in vars(args).items():
            k_type = getattr(cls, k).fget.__annotations__["return"]
            setattr(c, k, k_type(v))
        return c
