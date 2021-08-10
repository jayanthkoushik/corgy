import importlib
import inspect
import re
import shutil
import sys
import textwrap
from argparse import Action, BooleanOptionalAction, HelpFormatter, PARSER, SUPPRESS
from functools import cache, partial
from itertools import cycle
from types import ModuleType
from typing import Any, Optional, Sequence, Union
from unittest.mock import patch

__all__ = ["CorgyHelpFormatter"]

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


class _ColorHelper:
    """Wrapper around `crayons` library to colorize text."""

    crayons: Optional[ModuleType]

    def __init__(self, use_colors: Optional[bool] = None, skip_tty_check: bool = False):
        """Initialize the color helper.

        Args:
            use_colors: Whether to enable colored output. If None, coloring is enabled
                if the `crayons` library is available, and the output is a tty.
            skip_tty_check: Whether to skip checking if the output is a tty. Only used
                if `use_colors` is None.
        """
        if use_colors:
            try:
                self.crayons = importlib.import_module("crayons")
            except ImportError:
                raise ImportError(
                    "`crayons` library is required to use colors"
                ) from None
        elif use_colors is None and (skip_tty_check or sys.stdout.isatty()):
            try:
                self.crayons = importlib.import_module("crayons")
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

        if use_bold := color.isupper():
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

    def __setattr__(cls, name: str, value: Any):
        """Prevent new attributes from being set."""
        # Note: `__setattr__` applies to instances of the class, so `cls` here is a
        # class created using this metaclass.
        if name not in cls.__dict__:
            raise AttributeError(
                f"cannot set attribute `{name}` on class `{cls.__name__}`: "
                f"if you are trying to configure an existing attribute, "
                f"are you sure you're using the correct name?"
            )
        super().__setattr__(name, value)


class CorgyHelpFormatter(HelpFormatter, metaclass=_CorgyHelpFormatterMeta):
    """Formatter class for `argparse` with a cleaner layout, and support for colors.

    To use, pass this class as the `formatter_class` argument to
    `argparse.ArgumentParser`. To configure the behavior, first set attributes on the
    class itself.

    By default, colors are enabled if the `crayons` library is available, and the output
    is a tty. To force colors off, set `use_colors` to `False`. To set the colors used
    for choices, default values, keywords, metavars, and option strings, set
    `color_<choices/defaults/keywords/metavars/options>` to a valid `crayons` color
    name, or `BOLD`. If the color name is all caps, the text will be made bold. `BOLD`
    will make the text bold without coloring. The defaults are `blue`, `YELLOW`,
    `green`, `RED`, and `BOLD` respectively.

    To change the width to which the output is wrapped, set `output_width` to the
    desired value. If `None` (the default), the width is set to the current terminal
    width. `max_help_position` controls how far to the right the help text can start
    from. The default value is 40. If `None`, there is no limit.

    Extra help (e.g., choices, default values) is shown after the help text, enclosed
    between `marker_extras_begin` and `marker_extras_end` (defaults `(` and `)`
    respectively). Choices are enclosed between `marker_choices_begin` and
    `marker_choices_end` (defaults `[` and `]` respectively), and are separated by
    `marker_choices_sep` (default `/`).
    """

    use_colors: Optional[bool] = None
    color_choices = "blue"
    color_defaults = "YELLOW"
    color_keywords = "green"
    color_metavars = "RED"
    color_options = "BOLD"

    output_width: Optional[int] = None
    max_help_position: Optional[int] = 40

    marker_extras_begin = "("
    marker_extras_end = ")"
    marker_choices_begin = "{"
    marker_choices_end = "}"
    marker_choices_sep = "/"

    _color_helper: _ColorHelper

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

    @staticmethod
    @cache
    def _pattern_placeholder_text(placeholder) -> re.Pattern:
        """Regex to match text which has been replaced by the given placeholder."""
        # Due to wrapping, the placeholder text may be split across multiple lines. So,
        # the regex looks for a continuous string of `placeholder` or whitespace.
        return re.compile(rf"({placeholder}[{placeholder}\s]*)", re.DOTALL)

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
                match is replaced with a colored version of iteself.
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
                    while (rem_len := len(text_piece) - len(repl_piece)) > 0:
                        repl_piece += replacement[repl_idx : repl_idx + rem_len]
                        repl_idx += rem_len
                        if repl_idx >= len(replacement):
                            repl_idx = 0
                text_pieces[i] = self._color_helper.colorize(repl_piece, color)
        return "".join(text_pieces)

    def _get_default_metavar_for_optional(self, action: Action) -> str:
        """Metavar to use if none is explicityly provided.

        Special attribute `__metavar__` can be added to any type, to use a custom
        metavar for that type. Callable types use the return type, if it is annotated.
        Other types use the name of type itself.
        """
        if action.type:
            if (
                custom_metavar := getattr(action.type, "__metavar__", None)
            ) is not None:
                return custom_metavar

            if (
                callable(action.type)
                and (anno := getattr(action.type, "__annotations__", None))
                and (return_type := anno.get("return", None))
            ):
                with patch.object(action, "type", return_type):
                    return self._get_default_metavar_for_optional(action)

            return getattr(action.type, "__name__")

        return ""

    def _format_action_invocation(self, action: Action) -> str:
        """Format the invocation part of an argument, e.g. `-x, --x int`."""
        if action.option_strings:
            option_strings = action.option_strings
        else:
            # If no option strings are present, (positional arguments), use
            # `action.dest`. However, this can be `SUPPRESS` for sub-actions, in which
            # case use the word `CMD`.
            option_strings = [action.dest if action.dest != SUPPRESS else "CMD"]

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
        if action.nargs == PARSER:
            # No metavars for a sub-command.
            return ""

        metavar = action.metavar or default_metavar or ""

        if self.using_colors:
            # Create a placeholder for the metavar, and store it in the action.
            placeholder_metavar: Union[str, tuple[str, ...]]
            if isinstance(metavar, tuple):
                placeholder_metavar = tuple(
                    _PLACEHOLDER_METAVAR * len(metavar_i) for metavar_i in metavar
                )
            else:
                placeholder_metavar = _PLACEHOLDER_METAVAR * len(metavar)
            setattr(action, "_corgy_metavar", metavar)
        else:
            placeholder_metavar = metavar

        with patch.object(action, "metavar", placeholder_metavar):
            return super()._format_args(action, "")

    def _format_action(self, action: Action) -> str:
        """Format a single argument.

        The superclass implementation produces an output like
        `  --arg ARG   arg help`.

        This implementaiton includes the default value, and choices (if present). Text
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
        if action.choices:
            if self.using_colors:
                marker_choices_begin = _PLACEHOLDER_CHOICES_BEGIN
                marker_choices_end = _PLACEHOLDER_CHOICES_END
                marker_choices_sep = _PLACEHOLDER_CHOICES_SEP
            else:
                marker_choices_begin = self.marker_choices_begin
                marker_choices_end = self.marker_choices_end
                marker_choices_sep = self.marker_choices_sep
            choices_str = marker_choices_sep.join(list(map(repr, action.choices)))
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
            arg_qualifier = (
                _PLACEHOLDER_KWD_REQUIRED * len("required")
                if self.using_colors
                else "required"
            )
        elif action.default is None or action.default is SUPPRESS:
            arg_qualifier = (
                _PLACEHOLDER_KWD_OPTIONAL * len("optional")
                if self.using_colors
                else "optional"
            )
        else:
            if self.using_colors:
                arg_qualifier = (
                    (_PLACEHOLDER_KWD_DEFAULT * len("default"))
                    + ": "
                    + (_PLACEHOLDER_DEFAULT_VAL * len(repr(action.default)))
                )
            else:
                arg_qualifier = f"default: {action.default!r}"
            if isinstance(action, BooleanOptionalAction) and action.help:
                # BooleanOptionalAction adds the default value to the help text. Remove
                # it, since we already have it.
                action.help = action.help.removesuffix(f" (default: {action.default})")

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
        output_width = self.output_width or shutil.get_terminal_size().columns
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
        if (
            option_strings := getattr(action, "_corgy_option_strings", None)
        ) is not None:
            pattern = self._pattern_placeholder_text(_PLACEHOLDER_OPTION_STR)
            for option_string in option_strings:
                f_sub = partial(
                    self._sub_non_ws_with_colored_repl,
                    replacement=option_string,
                    color=self.color_options,
                )
                fmt = pattern.sub(f_sub, fmt, count=1)

        # Colorize the metavars.
        if (metavars := getattr(action, "_corgy_metavar", None)) is not None:
            if isinstance(metavars, str):
                metavars = (metavars,)
            if isinstance(action.nargs, int) and action.nargs > 0:
                # When `nargs` is a number, the metavar part is formatted as a space
                # separated sequence. So, all the metavars are captured together by
                # the regex (which allows whitespace between placeholders). So, we
                # combine the metavars into a single string, which will be passed to
                # `_sub_non_ws_with_colored_repl` to replace the entire metavar part.
                metavars = ("".join(metavars),)

            pattern = self._pattern_placeholder_text(_PLACEHOLDER_METAVAR)

            metavar_iter = iter(cycle(metavars))
            while match := pattern.search(fmt):
                metavar = next(metavar_iter)
                match_sub = self._sub_non_ws_with_colored_repl(
                    match, metavar, self.color_metavars
                )
                fmt = fmt[: match.start()] + match_sub + fmt[match.end() :]

        # Colorize the default value.
        if action.default is not None and action.default != SUPPRESS:
            pattern = self._pattern_placeholder_text(_PLACEHOLDER_DEFAULT_VAL)
            f_sub = partial(
                self._sub_non_ws_with_colored_repl,
                replacement=repr(action.default),
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
            }
        )

        return fmt

    def start_section(self, heading: Optional[str] = None) -> None:
        if heading == "optional arguments":
            # This was made the default in Python 3.10.
            heading = "options"
        super().start_section(heading)

    def add_usage(self, *args, **kwargs) -> None:
        # Only add usage if called directly from `ArgumentParser.format_usage`. This
        # prevents usage from being shown inside help output.
        current_frame = inspect.currentframe()
        if not current_frame:
            return
        caller_frame = current_frame.f_back
        if not caller_frame or caller_frame.f_code.co_name != "format_usage":
            return
        super().add_usage(*args, **kwargs)

    def _format_usage(self, usage, actions, groups, prefix) -> str:
        if usage is None:
            # Don't build usage from options, if it is not specified.
            return ""
        return super()._format_usage(usage, actions, groups, prefix)

    def __init__(self, prog: str) -> None:
        # noqa: D107
        self._color_helper = _ColorHelper(self.use_colors)
        # Wrapping is managed by this class, so pass `sys.maxsize` to the superclass.
        super().__init__(
            prog,
            max_help_position=sys.maxsize,
            width=sys.maxsize,
        )
