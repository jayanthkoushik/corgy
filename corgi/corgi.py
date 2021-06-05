import argparse
from collections.abc import Collection, Mapping
from contextlib import suppress
from typing import Any, Literal, Optional, Type, Union


class CorgiMeta(type):
    def __new__(cls, name, bases, namespace, **kwds):
        if "__annotations__" not in namespace:
            return super().__new__(cls, name, bases, namespace, **kwds)

        namespace["_defaults"] = dict()
        for var_name, var_ano in namespace["__annotations__"].items():
            # Check if help string is present
            if hasattr(var_ano, "__metadata__"):
                var_type = var_ano.__origin__
                var_help = var_ano.__metadata__[0]
                assert isinstance(var_help, str)
            else:
                var_type = var_ano
                var_help = None
            namespace["__annotations__"][var_name] = var_type

            # Add default value to dedicated dict
            with suppress(KeyError):
                namespace["_defaults"][var_name] = namespace[var_name]

            # Create 'var' property
            namespace[var_name] = cls._create_var_property(var_name, var_help)

        return super().__new__(cls, name, bases, namespace, **kwds)

    @staticmethod
    def _create_var_property(var_name, var_doc):
        def _var_fget(self):
            return getattr(self, f"_{var_name}")

        def _var_fset(self, val):
            setattr(self, f"_{var_name}", val)

        return property(_var_fget, _var_fset, var_doc)


class Corgi(metaclass=CorgiMeta):
    _defaults: dict[str, Any]

    def __getattr__(self, name):
        with suppress(KeyError):
            return self._defaults[name]
        raise AttributeError

    @classmethod
    def _add_args_to_parser(cls, parser: argparse.ArgumentParser):
        for var_name, var_type in cls.__annotations__.items():
            var_dashed_name = var_name.replace("_", "-")
            var_help = getattr(cls, var_name).__doc__
            var_default = cls._defaults.get(var_name)

            # Check if arg is a group
            if type(var_type) is type(cls):
                grp_parser = parser.add_argument_group(var_dashed_name, var_help)
                var_type._add_args_to_parser(grp_parser)
                continue

            # Check if arg is optional
            if (
                hasattr(var_type, "__origin__")
                and var_type.__origin__ is Union
                and var_type.__args__[1] is type(None)
            ):
                var_base_type = var_type.__args__[0]
                var_required = False
            else:
                var_base_type = var_type
                var_required = var_default is None

            # Check if arg is a collection
            var_nargs: Optional[Union[int, Literal["*", "+"]]]
            if (
                hasattr(var_base_type, "__origin__")
                and issubclass(var_base_type.__origin__, Collection)
                and not issubclass(var_base_type.__origin__, Mapping)
            ):
                if var_nargs := len(var_base_type.__args__) > 1:
                    assert all(
                        _a is var_base_type.__args__[0]
                        for _a in var_base_type.__args__[1:]
                    )
                else:
                    var_nargs = "+" if var_required else "*"
                var_base_type = var_base_type.__args__[0]
            else:
                var_nargs = None

            # Check if arg has choices
            if (
                hasattr(var_base_type, "__origin__")
                and var_base_type.__origin__ is Literal
            ):
                assert all(
                    type(_a) is type(var_base_type.__args__[0])
                    for _a in var_base_type.__args__
                )
                var_choices = var_base_type.__args__
                var_base_type = type(var_base_type.__args__[0])
            else:
                var_choices = None

            # Check if arg is boolean
            var_action: Optional[Type[argparse.Action]]
            if var_base_type is bool:
                var_action = argparse.BooleanOptionalAction
                var_required = False
            else:
                var_action = None

            # Add argument to parser
            _kwargs: Any = {}
            if var_nargs is not None:
                _kwargs["nargs"] = var_nargs
            if var_action is not None:
                _kwargs["action"] = var_action
            parser.add_argument(
                f"--{var_dashed_name}",
                type=var_base_type,
                help=var_help,
                required=var_required,
                default=var_default,
                choices=var_choices,
                **_kwargs,
            )
