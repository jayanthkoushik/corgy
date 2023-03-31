from __future__ import annotations

import argparse
import inspect
import re
import sys
import textwrap
from argparse import Action, ArgumentParser, HelpFormatter
from collections.abc import Sequence as AbstractSequence
from functools import lru_cache, partial
from importlib import import_module
from itertools import cycle, zip_longest
from shutil import get_terminal_size
from types import ModuleType
from typing import Optional, Sequence, Tuple, Union
from unittest.mock import patch

from ._actions import OptionalTypeAction
from ._meta import get_concrete_collection_type, is_optional_type

__all__ = ("CorgyHelpFormatter",)

# These placeholders are used to replace special characters and words, so they can be
# identified later for colorizing, without clashes with the help text. The code-points
# are non-character points from `U+FDD0` to `U+FDEF`, which are guaranteed to never be
# used for a character.
_PLACEHOLDER_OPTION_STR = "\ufdd0"
_PLACEHOLDER_METAVAR = "\ufdd1"
_PLACEHOLDER_DEFAULT_VAL = "\ufdd2"
_PLACEHOLDER_EXTRAS_BEGIN = "\ufdd3"
_PLACEHOLDER_EXTRAS_END = "\ufdd4"
_PLACEHOLDER_CHOICES_BEGIN = "\ufdd5"
_PLACEHOLDER_CHOICES_END = "\ufdd6"
_PLACEHOLDER_CHOICES_SEP = "\ufdd7"
_PLACEHOLDER_KWD_DEFAULT = "\ufdd8"
_PLACEHOLDER_KWD_OPTIONAL = "\ufdd9"
_PLACEHOLDER_KWD_REQUIRED = "\ufdda"
_PLACEHOLDER_METAVARS_BEGIN = "\ufddb"
_PLACEHOLDER_METAVARS_END = "\ufddc"
_PLACEHOLDER_METAVARS_REPEAT = "\ufddd"

# These markers are used by `argparse` to indicate metavar sequences, e.g.,
# `[int ...]`, `int [int ...]`.
_MARKER_METAVARS_BEGIN = "["
_MARKER_METAVARS_END = "]"
_MARKER_METAVARS_REPEAT = "..."


class ColorHelper:
    """Wrapper around `crayons` library to colorize text.

    Args:
        use_colors: Whether to enable colored output. If `None`, coloring is enabled
            if the `crayons` library is available, and the output is a tty.
        skip_tty_check: Whether to skip checking if the output is a tty. Only used if
            `use_colors` is None.
    """

    __slots__ = ("crayons",)
    crayons: Optional[ModuleType]

    def __init__(self, use_colors: Optional[bool] = None, skip_tty_check: bool = False):
        if use_colors:
            try:
                self.crayons = import_module("crayons")
            except ImportError:
                raise ImportError(
                    "`crayons` library is required to use colors"
                ) from None
        elif use_colors is None and (skip_tty_check or sys.stdout.isatty()):
            try:
                self.crayons = import_module("crayons")
            except ImportError:
                self.crayons = None
        else:
            self.crayons = None

    def colorize(self, text: str, color: str) -> str:
        """Colorize given text.

        Args:
            text: Text to colorize.
            color: Name of a valid `crayons` color. If the name is all caps, the text
                will be made bold. Special string `BOLD` will only make the text bold,
                without coloring.
        """
        if not self.crayons:
            return text

        if color == "BOLD":
            # `crayons` does not support only making text bold, so we have to use
            # `colorama` directly.
            colorama = getattr(self.crayons, "colorama")
            return colorama.Style.BRIGHT + text + colorama.Style.NORMAL

        use_bold = color.isupper()
        if use_bold:
            color = color.lower()
        try:
            f_color = getattr(self.crayons, color)
        except AttributeError:
            raise ValueError(f"invalid color: {color}") from None
        return str(f_color(text, bold=use_bold))


class _CorgyHelpFormatterMeta(type):
    """Metaclass for `CorgyHelpFormatter` which adds a `__setattr__` method.

    The method prevents new attributes from being set, primarily to prevent potential
    user errors caused by using an incorrect name to configure the class.
    """

    __slots__ = ()

    def __setattr__(cls, name, value):
        # Note: `__setattr__` applies to instances of the class, so `cls` here is a
        # class created using this metaclass.
        if name not in cls.__dict__:
            raise AttributeError(
                f"cannot set attribute `{name}` on class `{cls.__name__}`: if you are"
                f"trying to configure an existing attribute, are you sure you're using"
                f"the correct name?"
            )
        super().__setattr__(name, value)


class CorgyHelpFormatter(HelpFormatter, metaclass=_CorgyHelpFormatterMeta):
    """Formatter class for `argparse` with a cleaner layout, and support for colors.

    `Corgy.parse_from_cmdline` uses this formatter by default, unless a different
    `formatter_class` argument is provided. `CorgyHelpFormatter` can also be used
    independently of `Corgy`. Simply pass it as the `formatter_class` argument to
    `argparse.ArgumentParser()`::

        >>> import argparse
        >>> from argparse import ArgumentParser
        >>> from corgy import CorgyHelpFormatter

        >>> parser = ArgumentParser(
        ...     formatter_class=CorgyHelpFormatter,
        ...     usage=argparse.SUPPRESS,
        ... )
        >>> _ = parser.add_argument("--x", type=int, required=True)
        >>> _ = parser.add_argument("--y", type=str, nargs="*", required=True)
        >>> parser.print_help()
        options:
          -h/--help      show this help message and exit
          --x int        (required)
          --y [str ...]  (required)

    To configure `CorgyHelpFormatter`, you can set a number of attributes on the class.
    Note that you do not need to create an instance of the class; that is done by the
    parser itself. The following public attributes are available:

    * `enable_colors`: If `None` (the default), colors are enabled if the `crayons`
      package is available, and the output is a tty. To explicitly enable or disable
      colors, set to `True` or `False`.

    * `color_<choices/keywords/metavars/defaults/options>`: These attributes control
      the colors used for various parts of the output (see below for reference).
      Available colors are `red`, `green`, `yellow`, `blue`, `black`, `magenta`, `cyan`,
      and `white`. Specifying the name in all caps will make the color bold. You can
      also use the special value `BOLD` to make the output bold without changing the
      color. The default value are `blue` for choices, `green` for keywords, `RED` for
      metavars, `YELLOW` for defaults, and `BOLD` for options. Format:

      .. code-block:: text
         :dedent: 1

              -a/--arg str       help for arg ({'a'/'b'/'c'} default: 'a')
                |      |                          |            |      |
              options  metavars                 choices      keywords defaults

    * `output_width`: The number of columns used for the output. If `None` (the
      default), the current terminal width is used.

    * `max_help_position`: How far to the right (from the start), the help string can
      start from. If `None`, there is no limit. The default is to use half the current
      terminal width.

    * `marker_extras_<begin/end>`: The strings used to enclose the extra help text
      (choices, default values etc.). The defaults are `(` and `)`.

    * `marker_choices_<begin/end>`: The strings used to enclose the list of choices for
      an argument. The defaults are `{` and `}`.

    * `marker_choices_sep`: The string used to separate individual choices in the choice
      list. The default is `/`.

    * `show_full_help`: Whether to show the full help, including choices, indicators for
      required arguments, and the usage string. The default is `True`.

    Formatting of individual arguments can be customized with magic attributes defined
    on the argument type. The following attributes are recognized:

    * `__metavar__`: This can be set to a string on the argument type to override the
        default metavar. Example::

            >>> class T:
            ...     __metavar__ = "METAVAR"

            >>> parser = ArgumentParser(
            ...     formatter_class=CorgyHelpFormatter,
            ...     add_help=False,
            ...     usage=argparse.SUPPRESS,
            ... )
            >>> _ = parser.add_argument("--arg", type=T)
            >>> parser.print_help()
            options:
              --arg METAVAR  (default: None)

    """

    use_colors: Optional[bool] = None
    color_choices = "blue"
    color_defaults = "YELLOW"
    color_keywords = "green"
    color_metavars = "RED"
    color_options = "BOLD"

    output_width: Optional[int] = None
    max_help_position: Optional[int] = get_terminal_size().columns // 2

    marker_extras_begin = "("
    marker_extras_end = ")"
    marker_choices_begin = "{"
    marker_choices_end = "}"
    marker_choices_sep = "/"

    show_full_help = True

    __slots__ = ("_color_helper",)
    _color_helper: ColorHelper

    @property
    def using_colors(self) -> bool:
        """Whether colors are enabled."""
        return self._color_helper.crayons is not None

    # Regex to match a choice within a choice list, e.g., `b` in `{a/b/c}`.
    _pattern_choice = re.compile(
        f"(?<={_PLACEHOLDER_CHOICES_BEGIN}|{_PLACEHOLDER_CHOICES_SEP}).*?"
        f"(?={_PLACEHOLDER_CHOICES_END}|{_PLACEHOLDER_CHOICES_SEP})",
        re.DOTALL,
    )

    # Regex to match any character which is not a metavar extra.
    _pattern_not_metavar_extra = re.compile(
        f"[^{_PLACEHOLDER_METAVARS_BEGIN}{_PLACEHOLDER_METAVARS_END}"
        f"{_PLACEHOLDER_METAVARS_REPEAT}]"
    )

    @staticmethod
    @lru_cache(maxsize=None)
    def _pattern_placeholder_text(placeholder: str) -> re.Pattern:
        """Regex to match text which has been replaced by the given placeholder."""
        # Due to wrapping, the placeholder text may be split across multiple lines. So,
        # the regex looks for a continuous string of `placeholder` or whitespace.
        return re.compile(rf"({placeholder}[{placeholder}\s]*)", re.DOTALL)

    @staticmethod
    def _stringify(obj, type_) -> str:
        if isinstance(obj, (AbstractSequence, set)) and not isinstance(
            obj, (str, bytes)
        ):
            # `obj` is a collection: recursively apply `_stringify` on its elements.
            # `obj` has to be checked before `type_`, because the type may not be a
            # collection type when `nargs` is used to get multiple arguments.
            _coll_type = get_concrete_collection_type(type_)
            if _coll_type is not None and isinstance(
                getattr(type_, "__args__", None), AbstractSequence
            ):
                # `type_` is also a collection, so unwrap it to get the base type. This
                # happens in case of nested types like `Sequence[Sequence[int]]`.
                _base_types = type_.__args__
                if len(_base_types) == 2 and _base_types[1] is Ellipsis:
                    _base_types = _base_types[:1]
                elif len(_base_types) > 1 and len(_base_types) != len(obj):
                    raise ValueError(f"cannot format object as type '{type_}': {obj}")
            else:
                _base_types = [type_]
            _part_strs = [
                CorgyHelpFormatter._stringify(_part, _base_type)
                for _part, _base_type in zip_longest(
                    obj, _base_types, fillvalue=_base_types[-1]
                )
            ]
            _seq_start = "(" if _coll_type is tuple or isinstance(obj, tuple) else "["
            _seq_end = ")" if _seq_start == "(" else "]"
            return _seq_start + ", ".join(_part_strs) + _seq_end

        if is_optional_type(type_):
            # type_ is `Optional`; so unwrap to get the base type. This case happens
            # in cases like `Sequence[Optional[int]]`, where `Optional` is not the
            # outermost type.
            if obj is None:
                return "None"
            return CorgyHelpFormatter._stringify(obj, type_.__args__[0])

        try:
            return obj.__name__  # type: ignore
        except AttributeError:
            try:
                if isinstance(obj, type_):
                    return type_.__str__(obj)
            except TypeError:
                pass
            return str(obj)

    @staticmethod
    def _get_stringify_type_for_default(action):
        """Get the type that should be used to stringify `action.default`."""
        _stringify_type = action.type
        if isinstance(action.nargs, int) or action.nargs in (
            argparse.ZERO_OR_MORE,
            argparse.ONE_OR_MORE,
        ):
            # If the argument specifies nargs, and the default value is a,
            # collection, wrap the action type with the default collection type.
            if isinstance(action.default, tuple):
                _stringify_type = Tuple[action.type]  # type: ignore
            elif isinstance(action.default, AbstractSequence):
                _stringify_type = Sequence[action.type]  # type: ignore
        return _stringify_type

    def _sub_non_ws_with_colored_repl(
        self, match: re.Match, replacement: Optional[str], color: str
    ) -> str:
        """Replace non-whitespace characters in the match using colored replacement.

        For example, if the match is `aaa   aaaa a`, and the replacement is `bbbbbbbb`,
        the result will be `bbb   bbbb b` (with the `b`s colored).

        Args:
            match: The match to substitute into.
            replacement: The replacement to use. If it is shorter than the
                non-whitespace part of the match, it is repeated. If it is `None`, the
                match is replaced with a colored version of itself.
        """
        text = match.group(0)
        text_pieces = re.split(r"(\S+)", text)
        repl_idx = 0
        for i, text_piece in enumerate(text_pieces):
            # Since we split on non-whitespace, every other piece is text.
            if i % 2:
                if replacement is None:
                    repl_piece = text_piece
                else:
                    repl_piece = ""
                    while True:
                        rem_len = len(text_piece) - len(repl_piece)
                        if rem_len <= 0:
                            break
                        repl_piece += replacement[repl_idx : repl_idx + rem_len]
                        repl_idx += rem_len
                        if repl_idx >= len(replacement):
                            repl_idx = 0
                text_pieces[i] = self._color_helper.colorize(repl_piece, color)
        return "".join(text_pieces)

    @staticmethod
    def _get_default_metavar_for_type(type_, using_colors) -> str:
        """Metavar to use if none is explicitly provided.

        Special attribute `__metavar__` can be added to any type, to use a custom
        metavar for that type. Other types use the name of type itself.
        """
        if type_:
            custom_metavar = getattr(type_, "__metavar__", None)
            if custom_metavar is not None:
                return custom_metavar

            if using_colors:
                marker_metavars_begin = _PLACEHOLDER_METAVARS_BEGIN
                marker_metavars_end = _PLACEHOLDER_METAVARS_END
                marker_metavars_repeat = _PLACEHOLDER_METAVARS_REPEAT
            else:
                marker_metavars_begin = _MARKER_METAVARS_BEGIN
                marker_metavars_end = _MARKER_METAVARS_END
                marker_metavars_repeat = _MARKER_METAVARS_REPEAT

            _coll_type = get_concrete_collection_type(type_)
            if _coll_type is not None and (
                isinstance(getattr(type_, "__args__", None), AbstractSequence)
                and type_ is not Sequence
            ):
                # `action.type` is a collection. So, create a metavar list based on the
                # base type(s).
                _type_args = getattr(type_, "__args__")
                if len(_type_args) == 1 or (
                    len(_type_args) == 2 and _type_args[1] is Ellipsis
                ):
                    _base_metavar = CorgyHelpFormatter._get_default_metavar_for_type(
                        _type_args[0], using_colors
                    )
                    # '[<base_type> ...]'.
                    _metavar_repeat = (
                        marker_metavars_begin
                        + _base_metavar
                        + " "
                        + marker_metavars_repeat
                        + marker_metavars_end
                    )
                    if len(_type_args) == 1:
                        return _metavar_repeat
                    # '<base_type> [<base_type> ...]'.
                    return _base_metavar + " " + _metavar_repeat

                _part_metavars = []
                for _part_type in _type_args:
                    _part_metavars.append(
                        CorgyHelpFormatter._get_default_metavar_for_type(
                            _part_type, using_colors
                        )
                    )
                # '<base_type_1> <base_type_2> <...> <base_type_n>'.
                return " ".join(_part_metavars)

            if is_optional_type(type_):
                # `action.type` is optional. So, return '[<base metavar>]'.
                _base_type = getattr(type_, "__args__")[0]
                _s = (
                    marker_metavars_begin
                    + CorgyHelpFormatter._get_default_metavar_for_type(
                        _base_type, using_colors
                    )
                    + marker_metavars_end
                )
                return _s

            try:
                return getattr(type_, "__name__")
            except AttributeError:
                return str(type_)
        return ""

    def _get_default_metavar_for_optional(self, action: Action) -> str:
        return self._get_default_metavar_for_type(action.type, self.using_colors)

    def _format_action_invocation(self, action: Action) -> str:
        """Format the invocation part of an argument, e.g. `-x, --x int`."""
        if action.option_strings:
            option_strings = action.option_strings
        else:
            # If no option strings are present, (positional arguments), use
            # `action.dest`. However, this can be `argparse.SUPPRESS` for sub-actions,
            # in which case use the word `CMD`.
            option_strings = [
                action.dest if action.dest != argparse.SUPPRESS else "CMD"
            ]

        if self.using_colors:
            # Create placeholders for the option strings, and store originals.
            placeholder_option_strings: Sequence[str] = [
                _PLACEHOLDER_OPTION_STR * len(option_string)
                for option_string in option_strings
            ]
            setattr(action, "_corgy_option_strings", option_strings)
        else:
            placeholder_option_strings = option_strings

        # Combine the option strings so that they are shown like `-s/--long ARGS`,
        # rather than `-s ARGS, --long ARGS` (the default).
        with patch.object(
            action,
            "option_strings",
            [self.marker_choices_sep.join(placeholder_option_strings)],
        ):
            return super()._format_action_invocation(action).rstrip()

    def _format_args(self, action: Action, default_metavar: Optional[str]) -> str:
        """Format the metavars."""
        if action.nargs == argparse.PARSER:
            # No metavars for a sub-command.
            return ""

        metavar = action.metavar or default_metavar or ""

        if self.using_colors:
            # Create a placeholder for the metavar, and store it in the action.
            placeholder_metavar: Union[str, Tuple[str, ...]]

            def _placeholderize_metavar(_m):
                # Colors should not be applied to metavar extras, e.g., in
                # `[int ...]`, only `int` must be colored. So, this function
                # replaces non-extra characters with `_PLACEHOLDER_METAVAR`, and
                # returns the modified metavar and the replaced characters.
                _modded, _repl = [], []
                for _char in _m:
                    if _char in [
                        _PLACEHOLDER_METAVARS_BEGIN,
                        _PLACEHOLDER_METAVARS_END,
                        _PLACEHOLDER_METAVARS_REPEAT,
                        " ",
                    ]:
                        _modded.append(_char)
                    else:
                        _modded.append(_PLACEHOLDER_METAVAR)
                        _repl.append(_char)
                return "".join(_modded), "".join(_repl)

            if isinstance(metavar, tuple):
                placeholder_metavar, metavar = zip(
                    *tuple(_placeholderize_metavar(metavar_i) for metavar_i in metavar)
                )
            else:
                placeholder_metavar, metavar = _placeholderize_metavar(metavar)
            # Store the non-extra characters in the action, so they can be colorized
            # and substituted into the placeholder later.
            setattr(action, "_corgy_metavar", metavar)
        else:
            placeholder_metavar = metavar

        # For `corgy._corgy.OptionalTypeAction`s, use the true `nargs` for formatting.
        _fmt_nargs = (
            action._base_nargs
            if isinstance(action, OptionalTypeAction)
            else action.nargs
        )
        with patch.multiple(action, nargs=_fmt_nargs, metavar=placeholder_metavar):
            if action.nargs == argparse.ZERO_OR_MORE:
                # Python 3.9+ shows '*' argumets of a single type as `[<base_type> ...]`
                # instead of `[<base_type> [<base_type> ...]]`. This code backports that
                # functionality.
                _mv = self._metavar_formatter(action, "")(1)
                if len(_mv) == 2:
                    return f"[{_mv[0]} [{_mv[1]} ...]]"
                return f"[{_mv[0]} ...]"
            _fmt = super()._format_args(action, "")
            if isinstance(action, OptionalTypeAction):
                # Add `[]` around the metavar.
                _fmt = f"[{_fmt}]"
            return _fmt

    def _format_action(self, action: Action) -> str:
        """Format a single argument.

        The superclass implementation produces an output like
        `  --arg ARG   arg help`.

        This implementation includes the default value, and choices (if present). Text
        is added to indicate if the argument is required, or optional. The argument type
        is used as the metavar, and colors are used for semantic highlighting.
        """
        # First, generate base format without help text. This is the invocation part,
        # e.g., `--x str`, but with the correct amount of spacing appended, for proper
        # alignment with the other arguments. The help is replaced with a dummy `\0`,
        # since with an empty help, there would be no extra spacing added.
        with patch.object(action, "help", "\0"):
            base_fmt = super()._format_action(action)
        base_fmt = base_fmt[:-2]  # remove trailing `\0\n`

        # Create formatted choice list.
        if action.choices and self.show_full_help:
            if self.using_colors:
                marker_choices_begin = _PLACEHOLDER_CHOICES_BEGIN
                marker_choices_end = _PLACEHOLDER_CHOICES_END
                marker_choices_sep = _PLACEHOLDER_CHOICES_SEP
            else:
                marker_choices_begin = self.marker_choices_begin
                marker_choices_end = self.marker_choices_end
                marker_choices_sep = self.marker_choices_sep
            choices_str = marker_choices_sep.join(
                [self._stringify(choice, action.type) for choice in action.choices]
            )
            choice_list_fmt = (
                marker_choices_begin + choices_str + marker_choices_end + " "
            )
        else:
            choice_list_fmt = ""

        # Compute qualifier (`required`/`optional`/`default`).
        if not action.option_strings:
            # The argument is positional, so it can't be optional, and doesn't have a
            # default value. No extra help text is required, and the extra space added
            # above is removed here.
            if choice_list_fmt:
                choice_list_fmt = choice_list_fmt[:-1]
            arg_qualifier = ""
        elif action.required:
            if self.show_full_help:
                arg_qualifier = (
                    _PLACEHOLDER_KWD_REQUIRED * len("required")
                    if self.using_colors
                    else "required"
                )
            else:
                arg_qualifier = ""
        elif action.default is argparse.SUPPRESS:
            if action.nargs == 0:
                # The argument takes no values, so no need to explicitly indicate that
                # it is optional. For example, help and version actions are obviously
                # optional.
                arg_qualifier = ""
            else:
                arg_qualifier = (
                    _PLACEHOLDER_KWD_OPTIONAL * len("optional")
                    if self.using_colors
                    else "optional"
                )
        else:
            _stringify_type = self._get_stringify_type_for_default(action)
            if self.using_colors:
                arg_qualifier = (
                    (_PLACEHOLDER_KWD_DEFAULT * len("default"))
                    + ": "
                    + (
                        _PLACEHOLDER_DEFAULT_VAL
                        * len(self._stringify(action.default, _stringify_type))
                    )
                )
            else:
                arg_qualifier = (
                    f"default: {self._stringify(action.default, _stringify_type)}"
                )

        # Add qualifier to choice list e.g. `({a/b/c} required)`.
        if choice_list_fmt or arg_qualifier:
            if self.using_colors:
                marker_extras_begin = _PLACEHOLDER_EXTRAS_BEGIN
                marker_extras_end = _PLACEHOLDER_EXTRAS_END
            else:
                marker_extras_begin = self.marker_extras_begin
                marker_extras_end = self.marker_extras_end
            extra_help = (
                marker_extras_begin
                + choice_list_fmt
                + arg_qualifier
                + marker_extras_end
            )
        else:
            extra_help = ""

        # Wrap the text according to `output_width` and `max_help_position`.
        output_width = self.output_width or get_terminal_size().columns
        max_help_position = self.max_help_position or output_width
        if len(base_fmt) + self._current_indent < min(output_width, max_help_position):
            # Example of desired result:
            #     --arg str  the help begins here,
            #                and continue here,
            #                and ends here (optional)
            indent = " " * len(base_fmt)
            base_after_wrap = False  # see below
        else:
            # In this case, the help text cannot start on the first line. So, the help
            # is separately wrapped, and the base format is preprended to it. Example:
            #     --very-very-long-arg-name str
            #         the help begins on the next line
            #         and can extend up to `help_width`.
            #         (optional)
            indent = " " * (self._current_indent + 2 * self._indent_increment)
            base_after_wrap = True  # whether to prepend `base_fmt` after wrapping

            # Since the base format is prepended, it needs to be separately wrapped
            base_fmt = base_fmt.lstrip()
            base_fmt = textwrap.fill(
                base_fmt,
                width=output_width,
                initial_indent=" " * self._current_indent,
                subsequent_indent=" " * (self._current_indent + self._indent_increment),
                break_on_hyphens=False,
            )

        # Combine the base format with the help string and the choice list.
        fmt = "" if base_after_wrap else base_fmt
        if action.help:
            fmt += action.help
        if extra_help:
            fmt += (" " if action.help else "") + extra_help

        fmt = textwrap.fill(
            fmt,
            width=output_width,
            initial_indent=indent if base_after_wrap else "",
            subsequent_indent=indent,
            break_on_hyphens=False,
        )
        if base_after_wrap:
            fmt = base_fmt + "\n" + fmt
        fmt = fmt + "\n"

        if not self.using_colors:
            return fmt

        # Colorize the keywords.
        for kwd, placeholder_kwd in zip(
            ["default", "optional", "required"],
            [
                _PLACEHOLDER_KWD_DEFAULT,
                _PLACEHOLDER_KWD_OPTIONAL,
                _PLACEHOLDER_KWD_REQUIRED,
            ],
        ):
            pattern = self._pattern_placeholder_text(placeholder_kwd)
            f_sub = partial(
                self._sub_non_ws_with_colored_repl,
                replacement=kwd,
                color=self.color_keywords,
            )
            fmt = pattern.sub(f_sub, fmt)

        # Colorize the option strings.
        option_strings = getattr(action, "_corgy_option_strings", None)
        if option_strings is not None:
            pattern = self._pattern_placeholder_text(_PLACEHOLDER_OPTION_STR)
            for option_string in option_strings:
                f_sub = partial(
                    self._sub_non_ws_with_colored_repl,
                    replacement=option_string,
                    color=self.color_options,
                )
                fmt = pattern.sub(f_sub, fmt, count=1)

        # Colorize the metavars.
        metavars = getattr(action, "_corgy_metavar", None)
        if metavars is not None:
            if isinstance(metavars, str):
                metavars = (metavars,)
            if isinstance(action.nargs, int) and action.nargs > 0:
                # When `nargs` is a number, the metavar part is formatted as a space
                # separated sequence. So, all the metavars are captured together by the
                # regex (which allows whitespace between placeholders). So, we combine
                # the metavars into a single string, which will be passed to
                # `_sub_non_ws_with_colored_repl` to replace the entire metavar part.
                metavars = ("".join(metavars),)

            pattern = self._pattern_placeholder_text(_PLACEHOLDER_METAVAR)

            metavar_iter = iter(cycle(metavars))
            while True:
                match = pattern.search(fmt)
                if not match:
                    break
                metavar = next(metavar_iter)
                match_sub = self._sub_non_ws_with_colored_repl(
                    match, metavar, self.color_metavars
                )
                fmt = fmt[: match.start()] + match_sub + fmt[match.end() :]

        # Colorize the default value.
        if action.default != argparse.SUPPRESS:
            pattern = self._pattern_placeholder_text(_PLACEHOLDER_DEFAULT_VAL)
            _stringify_type = self._get_stringify_type_for_default(action)
            f_sub = partial(
                self._sub_non_ws_with_colored_repl,
                replacement=self._stringify(action.default, _stringify_type),
                color=self.color_defaults,
            )
            fmt = pattern.sub(f_sub, fmt)

        # Colorize the choices.
        f_sub = partial(
            self._sub_non_ws_with_colored_repl,
            replacement=None,  # the actual choices are in the regex match
            color=self.color_choices,
        )
        fmt = self._pattern_choice.sub(f_sub, fmt)

        # Replace placeholders.
        fmt = fmt.translate(
            {
                ord(_PLACEHOLDER_CHOICES_BEGIN): self.marker_choices_begin,
                ord(_PLACEHOLDER_CHOICES_END): self.marker_choices_end,
                ord(_PLACEHOLDER_CHOICES_SEP): self.marker_choices_sep,
                ord(_PLACEHOLDER_EXTRAS_BEGIN): self.marker_extras_begin,
                ord(_PLACEHOLDER_EXTRAS_END): self.marker_extras_end,
                ord(_PLACEHOLDER_METAVARS_BEGIN): _MARKER_METAVARS_BEGIN,
                ord(_PLACEHOLDER_METAVARS_END): _MARKER_METAVARS_END,
                ord(_PLACEHOLDER_METAVARS_REPEAT): _MARKER_METAVARS_REPEAT,
            }
        )

        return fmt

    def start_section(self, heading: Optional[str] = None):
        #: :meta private:
        # 'optional arguments' was changed to 'options' in Python 3.10.
        heading = "options" if heading == "optional arguments" else heading
        super().start_section(heading)

    def add_usage(self, *args, **kwargs):
        #: :meta private:
        if self.show_full_help:
            super().add_usage(*args, **kwargs)
            return

        # Only add usage if called directly from `ArgumentParser.format_usage`. This
        # prevents usage from being shown inside help output when `show_full_help` is
        # `False`.
        current_frame = inspect.currentframe()
        while current_frame:
            if current_frame.f_code.co_name == "format_usage":
                super().add_usage(*args, **kwargs)
                break
            current_frame = current_frame.f_back

    def _format_usage(self, usage: Optional[str], *args, **kwargs) -> str:
        with patch.object(self._color_helper, "crayons", None):
            # Disable colors for usage string.
            fmt = super()._format_usage(usage, *args, **kwargs)

        output_width = self.output_width or get_terminal_size().columns
        # Wrap usage to output width.
        fmt = textwrap.fill(
            fmt,
            width=output_width,
            subsequent_indent=" " * self._indent_increment,
            break_on_hyphens=False,
        )
        return fmt + "\n"

    def __init__(self, prog: str):
        # noqa: D107
        self._color_helper = ColorHelper(self.use_colors)
        # Wrapping is managed by this class, so pass `sys.maxsize` to the superclass.
        super().__init__(prog, max_help_position=sys.maxsize, width=sys.maxsize)

    class ShortHelpAction(Action):
        """`argparse.Action` that displays the short help, and exits."""

        def __call__(self, parser, namespace, values, option_string=None):
            CorgyHelpFormatter.show_full_help = False
            parser.print_help()
            parser.exit()

    class FullHelpAction(Action):
        """`argparse.Action` that displays the full help, and exits."""

        def __call__(self, parser, namespace, values, option_string=None):
            CorgyHelpFormatter.show_full_help = True
            parser.print_help()
            parser.exit()

    @classmethod
    def add_short_full_helps(
        cls,
        parser: ArgumentParser,
        short_help_flags: Sequence[str] = ("-h", "--help"),
        full_help_flags: Sequence[str] = ("--helpfull",),
        short_help_msg: str = "show help message and exit",
        full_help_msg: str = "show full help message and exit",
    ):
        """Add arguments for displaying the short or full help.

        The parser must be created with `add_help=False` to prevent a clash with the
        added arguments.

        Args:
            parser: `ArgumentParser` instance to add the arguments to.
            short_help_flags: Sequence of argument strings for the short help option.
                Default is `("-h", "--help")`.
            full_help_flags: Sequence of argument strings for the full help option.
                Default is `("--helpfull")`.
            short_help_msg: String to describe the short help option. Default is `"show
                help message and exit"`.
            full_help_msg: String to describe the full help option. Default is `"show
                full help message and exit"`.

        Example::

            >>> parser = ArgumentParser(
            ...     formatter_class=CorgyHelpFormatter,
            ...     add_help=False,
            ...     usage=argparse.SUPPRESS,
            ... )
            >>> CorgyHelpFormatter.add_short_full_helps(parser)
            >>> parser.print_help()
            options:
              -h/--help   show help message and exit
              --helpfull  show full help message and exit

        """
        parser.add_argument(
            *short_help_flags,
            nargs=0,
            action=cls.ShortHelpAction,
            help=short_help_msg,
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            *full_help_flags,
            nargs=0,
            action=cls.FullHelpAction,
            help=full_help_msg,
            default=argparse.SUPPRESS,
        )
