from __future__ import annotations

from argparse import Action, ArgumentError


class BooleanOptionalAction(Action):
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


class OptionalTypeAction(Action):
    """Action for parsing types wrapped in `Optional`."""

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._base_nargs = nargs
        if nargs is None or nargs == 1 or nargs == "?":
            nargs = "?"
        else:
            nargs = "*"
        super().__init__(option_strings, dest, nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        # `values` can be `None`, a single value, or a list of values.
        if values is None:
            setattr(namespace, self.dest, None)
            return

        if isinstance(values, list):
            if not values:
                # Empty list: set to `None`.
                setattr(namespace, self.dest, None)
                return

            # If not empty, check that the list matches the base nargs.
            _len_matches = True
            if self._base_nargs in (None, 1, "?"):
                _len_matches = len(values) == 1
                _err_msg = "expected at most one argument"
            elif isinstance(self._base_nargs, int):
                _len_matches = len(values) == self._base_nargs
                _err_msg = f"expected zero arguments or exactly {self._base_nargs}"
            if not _len_matches:
                raise ArgumentError(self, _err_msg)

        setattr(namespace, self.dest, values)
