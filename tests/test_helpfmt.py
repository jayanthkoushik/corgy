import argparse
import sys
from argparse import ArgumentParser
from typing import Optional
from unittest import skipIf, TestCase
from unittest.mock import Mock, patch

if sys.version_info < (3, 9):
    from typing import Sequence, Tuple
else:
    from collections.abc import Sequence  # pylint: disable=reimported

    Tuple = tuple  # type: ignore

from corgy import Corgy, CorgyHelpFormatter, NotRequired, Required
from corgy._corgy import BooleanOptionalAction
from corgy._helpfmt import ColorHelper
from corgy.types import KeyValuePairs

_COLOR_HELPER = ColorHelper(skip_tty_check=True)
_CRAYONS = _COLOR_HELPER.crayons

# Shortcuts for color functions to make ground truths in assert statements concise.
_M = lambda s: _COLOR_HELPER.colorize(s, CorgyHelpFormatter.color_metavars)
_K = lambda s: _COLOR_HELPER.colorize(s, CorgyHelpFormatter.color_keywords)
_C = lambda s: _COLOR_HELPER.colorize(s, CorgyHelpFormatter.color_choices)
_D = lambda s: _COLOR_HELPER.colorize(s, CorgyHelpFormatter.color_defaults)
_O = lambda s: _COLOR_HELPER.colorize(s, CorgyHelpFormatter.color_options)

# Shortcut for `default: None`.
_DNone = lambda: f"{_K('default')}: {_D('None')}"

# Make outputs independent of terminal width.
CorgyHelpFormatter.output_width = 80
CorgyHelpFormatter.max_help_position = 80


def setUpModule():
    # The default choice list end markers, `{`, `}`, make f-strings messy, since they
    # need to be escaped. So, we  replace them with `[`, `]`.
    CorgyHelpFormatter.marker_choices_begin = "["
    CorgyHelpFormatter.marker_choices_end = "]"


def tearDownModule():
    CorgyHelpFormatter.marker_choices_begin = "{"
    CorgyHelpFormatter.marker_choices_end = "}"


class TestCorgyHelpFormatterAPI(TestCase):
    def test_corgy_help_formatter_raises_if_enabling_colors_without_crayons(self):
        CorgyHelpFormatter.use_colors = True
        with patch("corgy._helpfmt.import_module", Mock(side_effect=ImportError)):
            with self.assertRaises(ImportError):
                ArgumentParser(formatter_class=CorgyHelpFormatter)

    def test_corgy_help_formatter_doesnt_raise_if_use_colors_none_without_crayons(self):
        CorgyHelpFormatter.use_colors = None
        with patch("corgy._helpfmt.import_module", Mock(side_effect=ImportError)):
            ArgumentParser(formatter_class=CorgyHelpFormatter)

    def test_corgy_help_formatter_raises_if_setting_new_attribute(self):
        with self.assertRaises(AttributeError):
            CorgyHelpFormatter.foo = "bar"

    @skipIf(_CRAYONS is None, "`crayons` package not found")
    def test_corgy_help_formatter_handles_changing_colors(self):
        CorgyHelpFormatter.use_colors = True
        with patch.multiple(
            CorgyHelpFormatter,
            color_choices="red",
            color_defaults="BLUE",
            color_keywords="BOLD",
            color_metavars="BLUE",
            color_options="yellow",
        ):
            parser = ArgumentParser(
                formatter_class=CorgyHelpFormatter,
                add_help=False,
                usage=argparse.SUPPRESS,
            )
            parser.add_argument(
                "--x", type=int, choices=[1, 2], help="x help", default=1
            )

            self.assertEqual(
                parser.format_help(),
                # options:
                #   --x int  x help ([1/2] default: 1)
                f"options:\n"
                f"  {_COLOR_HELPER.colorize('--x', 'yellow')} "
                f"{_COLOR_HELPER.colorize('int', 'BLUE')}  "
                f"x help ([{_COLOR_HELPER.colorize(1, 'red')}/"
                f"{_COLOR_HELPER.colorize(2, 'red')}] "
                f"{_COLOR_HELPER.colorize('default', 'BOLD')}: "
                f"{_COLOR_HELPER.colorize(1, 'BLUE')})\n",
            )

    def test_corgy_help_formatter_handles_changing_markers(self):
        CorgyHelpFormatter.use_colors = False
        with patch.multiple(
            CorgyHelpFormatter,
            marker_extras_begin="%",
            marker_extras_end="%",
            marker_choices_begin=" ( ",
            marker_choices_end=" ) ",
            marker_choices_sep="|",
        ):
            parser = ArgumentParser(
                formatter_class=CorgyHelpFormatter,
                add_help=False,
                usage=argparse.SUPPRESS,
            )
            parser.add_argument(
                "-x", "--x", type=int, choices=[1, 2], default=argparse.SUPPRESS
            )

            self.assertEqual(
                parser.format_help(), "options:\n  -x|--x int  % ( 1|2 )  optional%\n"
            )

    def test_corgy_help_formatter_handles_changing_output_width(self):
        CorgyHelpFormatter.use_colors = False
        with patch.object(CorgyHelpFormatter, "output_width", 10):
            parser = ArgumentParser(
                formatter_class=CorgyHelpFormatter, add_help=False, prog=""
            )
            parser.add_argument(
                "--x", type=int, help="x help", default=argparse.SUPPRESS
            )

            self.assertEqual(
                parser.format_help(),
                "usage:\n"
                "  [--x\n"
                "  int]\n\n"
                "options:\n"
                "  --x int\n"
                "      x\n"
                "      help\n"
                "      (opt\n"
                "      iona\n"
                "      l)\n",
            )

    def test_corgy_help_formatter_handles_changing_max_help_position(self):
        CorgyHelpFormatter.use_colors = False
        with patch.multiple(CorgyHelpFormatter, output_width=100, max_help_position=10):
            parser = ArgumentParser(
                formatter_class=CorgyHelpFormatter, usage=argparse.SUPPRESS
            )
            parser.add_argument(
                "--x", type=int, metavar="A LONG METAVAR", help="x help"
            )

            self.assertEqual(
                parser.format_help(),
                # options:
                #   -h/--help
                #       show this help message and exit
                #   --x A LONG METAVAR
                #       x help (default: None)
                "options:\n"
                "  -h/--help\n"
                "      show this help message and exit\n"
                "  --x A LONG METAVAR\n"
                "      x help (default: None)\n",
            )

    def test_corgy_help_formatter_handles_changing_show_full_help(self):
        CorgyHelpFormatter.use_colors = False
        with patch.object(CorgyHelpFormatter, "show_full_help", False):
            parser = ArgumentParser(
                formatter_class=CorgyHelpFormatter,
                add_help=False,
                usage="this shouldn't show",
            )
            parser.add_argument("--x", type=int, help="x help", required=True)
            parser.add_argument("--y", type=int, help="y help", choices=(1, 2))
            parser.add_argument("--z", type=int, help="z help", default=0)

            self.assertEqual(
                parser.format_help(),
                # options:
                #   --x int  x help
                #   --y int  y help (default: None)
                #   --z int  z help (default: 0)
                "options:\n"
                "  --x int  x help\n"
                "  --y int  y help (default: None)\n"
                "  --z int  z help (default: 0)\n",
            )

    @skipIf(_CRAYONS is None, "`crayons` package not found")
    def test_corgy_help_formatter_consistent_on_repeat_usage(self):
        CorgyHelpFormatter.use_colors = True
        parser = ArgumentParser(formatter_class=CorgyHelpFormatter, prog="")
        parser.add_argument("--x", type=int, choices=[1, 2])

        desired_output = (
            # usage: [-h] [--x int]
            #
            # options:
            #   -h/--help  show this help message and exit
            #   --x int    ([1/2] default: None)
            f"usage: [-h] [--x int]\n\n"
            f"options:\n"
            f"  {_O('-h')}/{_O('--help')}  show this help message and exit\n"
            f"  {_O('--x')} {_M('int')}    ([{_C(1)}/{_C(2)}] {_DNone()})\n"
        )

        self.assertEqual(parser.format_help(), desired_output)
        self.assertEqual(parser.format_help(), desired_output)

        # Test with a new parser.
        parser = ArgumentParser(formatter_class=CorgyHelpFormatter, prog="")
        parser.add_argument("--x", type=int, choices=[1, 2])
        self.assertEqual(parser.format_help(), desired_output)

    @skipIf(_CRAYONS is None, "`crayons` package not found")
    def test_corgy_help_formatter_raises_if_using_invalid_color(self):
        with patch.object(CorgyHelpFormatter, "color_metavars", "ELUB"):
            parser = ArgumentParser(
                formatter_class=CorgyHelpFormatter, usage=argparse.SUPPRESS
            )
            parser.add_argument("--x", type=str)
            with self.assertRaises(ValueError):
                parser.format_help()


class TestCorgyHelpFormatterHelpActions(TestCase):
    def setUp(self):
        CorgyHelpFormatter.use_colors = False
        self.parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )
        self.parser.print_help = Mock()
        self.parser.exit = Mock()

    def tearDown(self):
        CorgyHelpFormatter.show_full_help = True

    def test_corgy_help_formatter_short_help_action(self):
        self.parser.add_argument(
            "-h", nargs=0, action=CorgyHelpFormatter.ShortHelpAction
        )
        self.parser.parse_args(["-h"])  # pylint: disable=too-many-function-args (???)
        self.parser.print_help.assert_called_once()
        self.parser.exit.assert_called_once()
        self.assertEqual(CorgyHelpFormatter.show_full_help, False)

    def test_corgy_help_formatter_full_help_action(self):
        self.parser.add_argument(
            "-h", nargs=0, action=CorgyHelpFormatter.FullHelpAction
        )
        self.parser.parse_args(["-h"])  # pylint: disable=too-many-function-args (???)
        self.parser.print_help.assert_called_once()
        self.parser.exit.assert_called_once()
        self.assertEqual(CorgyHelpFormatter.show_full_help, True)

    def test_corgy_help_formatter_add_short_full_helps(self):
        self.parser.add_argument = Mock()
        CorgyHelpFormatter.add_short_full_helps(
            self.parser,
            short_help_flags=("-h", "--helpshort"),
            full_help_flags=("-H", "--helpfull"),
            short_help_msg="show short help",
            full_help_msg="show full help",
        )
        self.parser.add_argument.assert_any_call(
            "-h",
            "--helpshort",
            nargs=0,
            action=CorgyHelpFormatter.ShortHelpAction,
            help="show short help",
            default=argparse.SUPPRESS,
        )
        self.parser.add_argument.assert_any_call(
            "-H",
            "--helpfull",
            nargs=0,
            action=CorgyHelpFormatter.FullHelpAction,
            help="show full help",
            default=argparse.SUPPRESS,
        )


@skipIf(_CRAYONS is None, "`crayons` package not found")
class TestCorgyHelpFormatterSingleArgs(TestCase):
    def setUp(self):
        _COLOR_HELPER.crayons = _CRAYONS
        CorgyHelpFormatter.use_colors = True
        self.parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )
        self.maxDiff = None  # color codes can lead to very long diffs

    def _get_arg_help(self, *args, **kwargs):
        """Add a parser argument using `args` and `kwargs`, and return the help output.

        Only the output for the particular argument is returned.
        """
        self.parser.add_argument(*args, **kwargs)
        _help = self.parser.format_help()
        if _help:
            return _help.split("\n", maxsplit=1)[1].rstrip()
        return ""

    def test_corgy_help_formatter_handles_positional_arg_without_help(self):
        self.assertEqual(
            self._get_arg_help("arg", type=str),
            #   arg str
            f"  {_O('arg')} {_M('str')}",
        )

    def test_corgy_help_formatter_handles_required(self):
        self.assertEqual(
            self._get_arg_help("--x", type=str, required=True),
            #   --x str  (required)
            f"  {_O('--x')} {_M('str')}  ({_K('required')})",
        )

    def test_corgy_help_formatter_handles_optional(self):
        self.assertEqual(
            self._get_arg_help("--x", type=str, default=argparse.SUPPRESS),
            #   --x str  (optional)
            f"  {_O('--x')} {_M('str')}  ({_K('optional')})",
        )

    def test_corgy_help_formatter_handles_default(self):
        self.assertEqual(
            self._get_arg_help("--x", type=str, default="def"),
            #   --x str  (default: def)
            f"  {_O('--x')} {_M('str')}  ({_K('default')}: {_D('def')})",
        )

    def test_corgy_help_formatter_handles_choices(self):
        self.assertEqual(
            self._get_arg_help("--x", type=str, choices=["a", "b"]),
            #   --x str  ([a/b] default: None)
            f"  {_O('--x')} {_M('str')}  ([{_C('a')}/{_C('b')}] {_DNone()})",
        )

    def test_corgy_help_formatter_handles_choices_with_default(self):
        self.assertEqual(
            self._get_arg_help("--x", type=str, default="def", choices=["a", "b"]),
            #  --x str  ([a/b] default: def)
            f"  {_O('--x')} {_M('str')}  ([{_C('a')}/{_C('b')}] "
            f"{_K('default')}: {_D('def')})",
        )

    def test_corgy_help_formatter_handles_help_text(self):
        self.assertEqual(
            self._get_arg_help("--x", help="x help", type=str),
            #   --x str  x help (default: None)
            f"  {_O('--x')} {_M('str')}  x help ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_option_aliases(self):
        self.assertEqual(
            self._get_arg_help("-x", "--ex", "--between-y-and-z", type=str),
            # -x/--ex/--between-y-and-z str  (default: None)
            f"  {_O('-x')}/{_O('--ex')}/{_O('--between-y-and-z')} {_M('str')}  "
            f"({_DNone()})",
        )

    def test_corgy_help_formatter_handles_long_option(self):
        with patch.object(CorgyHelpFormatter, "output_width", 10):
            self.assertEqual(
                self._get_arg_help(
                    "--avery-long-argument-name", type=str, default=argparse.SUPPRESS
                ),
                #   --avery-
                #     long-a
                #     rgumen
                #     t-name
                #     str
                #       (opt
                #       iona
                #       l)
                f"  {_O('--avery-')}\n"
                f"    {_O('long-a')}\n"
                f"    {_O('rgumen')}\n"
                f"    {_O('t-name')}\n"
                f"    {_M('str')}\n"
                f"      ({_K('opt')}\n"
                f"      {_K('iona')}\n"
                f"      {_K('l')})",
            )

    def test_corgy_help_formatter_handles_different_prefix_chars(self):
        with patch.object(self.parser, "prefix_chars", "+++"):
            self.assertEqual(
                self._get_arg_help("+++x", type=str, help="x help"),
                #   +++x str  x help (default: None)
                f"  {_O('+++x')} {_M('str')}  x help ({_DNone()})",
            )

    def test_corgy_help_formatter_handles_boolean_optional_action(self):
        self.assertEqual(
            self._get_arg_help(
                "--x", action=BooleanOptionalAction, help="x help", default=True
            ),
            #   --x/--no-x  x help (default: True)
            f"  {_O('--x')}/{_O('--no-x')}  x help ({_K('default')}: {_D(True)})",
        )

    def test_corgy_help_formatter_handles_help_suppress(self):
        self.assertEqual(
            self._get_arg_help("--x", type=str, help=argparse.SUPPRESS, default="def"),
            "",
        )

    def test_corgy_help_formatter_handles_nargs_plus(self):
        self.assertEqual(
            self._get_arg_help("--x", nargs="+", type=str),
            #   --x str [str ...]  (default: None)
            f"  {_O('--x')} {_M('str')} [{_M('str')} ...]  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_nargs_star(self):
        self.assertEqual(
            self._get_arg_help("--x", nargs="*", type=str),
            f"  {_O('--x')} [{_M('str')} ...]  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_nargs_star_with_tuple_metavar(self):
        self.assertEqual(
            self._get_arg_help("--x", nargs="*", type=str, metavar=("a", "b")),
            f"  {_O('--x')} [{_M('a')} [{_M('b')} ...]]  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_nargs_const(self):
        self.assertEqual(
            self._get_arg_help("--x", nargs=3, type=str),
            #   --x str str str  (default: None)
            f"  {_O('--x')} {_M('str')} {_M('str')} {_M('str')}  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_nargs_suppress(self):
        self.assertEqual(
            self._get_arg_help("--x", nargs=argparse.SUPPRESS, type=str),
            #   --x  (default: None)
            f"  {_O('--x')}  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_tuple_metavar(self):
        self.assertEqual(
            self._get_arg_help("--x", metavar=("M1", "M2"), nargs=2),
            #   --x M1 M2  (default: None)
            f"  {_O('--x')} {_M('M1')} {_M('M2')}  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_tuple_metavar_with_nargs_plus(self):
        self.assertEqual(
            self._get_arg_help("--x", metavar=("M1", "M2"), nargs="+"),
            #   --x M1 [M2 ...]  (default: None)
            f"  {_O('--x')} {_M('M1')} [{_M('M2')} ...]  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_custom_type(self):
        class CustomType:
            ...

        self.assertEqual(
            self._get_arg_help("--x", type=CustomType),
            #   --x CustomType  (default: None)
            f"  {_O('--x')} {_M('CustomType')}  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_callable_type(self):
        def custom_type(s):
            return s

        self.assertEqual(
            self._get_arg_help("--x", type=custom_type, default="x"),
            #   --x custom_type  (optional)
            f"  {_O('--x')} {_M('custom_type')}  ({_K('default')}: {_D('x')})",
        )

    def test_corgy_help_formatter_handles_custom_metavar(self):
        class CustomType:
            __metavar__ = "CUSTOM"

        self.assertEqual(
            self._get_arg_help("--x", type=CustomType),
            #   --x CUSTOM  (default: None)
            f"  {_O('--x')} {_M('CUSTOM')}  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_missing_type(self):
        self.assertEqual(
            self._get_arg_help("--x", type=None),
            #   --x  (default: None)
            f"  {_O('--x')}  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_bad_type(self):
        class T:
            def __call__(self):
                ...

            def __str__(self):
                return "BAD"

        self.assertEqual(
            self._get_arg_help("--x", type=T()),
            #   --x BAD  (default: None)
            f"  {_O('--x')} {_M('BAD')}  ({_DNone()})",
        )

    def test_corgy_help_formatter_handles_long_metavar(self):
        class CustomType:
            __metavar__ = "A-VERY-VERY-LONG-METAVAR"

        with patch.object(CorgyHelpFormatter, "output_width", 10):
            self.assertEqual(
                self._get_arg_help("--x", type=CustomType, default=argparse.SUPPRESS),
                #   --x A-VE
                #     RY-VER
                #     Y-LONG
                #     -METAV
                #     AR
                #       (opt
                #       iona
                #       l)
                f"  {_O('--x')} {_M('A-VE')}\n"
                f"    {_M('RY-VER')}\n"
                f"    {_M('Y-LONG')}\n"
                f"    {_M('-METAV')}\n"
                f"    {_M('AR')}\n"
                f"      ({_K('opt')}\n"
                f"      {_K('iona')}\n"
                f"      {_K('l')})",
            )

    def test_corgy_help_formatter_handles_long_help(self):
        with patch.object(CorgyHelpFormatter, "output_width", 15):
            self.assertEqual(
                self._get_arg_help(
                    "--x",
                    type=str,
                    help="a very lengthy help",
                    default=argparse.SUPPRESS,
                ),
                #   --x str  a
                #            very
                #            leng
                #            thy
                #            help
                #            (opt
                #            iona
                #            l)
                f"  {_O('--x')} {_M('str')}  a\n"
                f"           very\n"
                f"           leng\n"
                f"           thy\n"
                f"           help\n"
                f"           ({_K('opt')}\n"
                f"           {_K('iona')}\n"
                f"           {_K('l')})",
            )

    def test_corgy_help_formatter_handles_long_help_with_small_max_help_pos(self):
        with patch.multiple(CorgyHelpFormatter, output_width=15, max_help_position=5):
            self.assertEqual(
                self._get_arg_help(
                    "--x",
                    type=str,
                    help="a very lengthy help",
                    default=argparse.SUPPRESS,
                ),
                #   --x str
                #       a very
                #       lengthy
                #       help (opt
                #       ional)
                f"  {_O('--x')} {_M('str')}\n"
                f"      a very\n"
                f"      lengthy\n"
                f"      help ({_K('opt')}\n"
                f"      {_K('ional')})",
            )

    def test_corgy_help_formatter_handles_conflicting_text_in_help(self):
        self.assertEqual(
            self._get_arg_help(
                "--x",
                type=int,
                choices=[1, 2],
                default=1,
                help="--x int  x help ([1/2] default: 1)",
            ),
            #   --x int  x help ([1/2] default: 1) ([1/2] default: 1)
            f"  {_O('--x')} {_M('int')}  --x int  x help ([1/2] default: 1) "
            f"([{_C(1)}/{_C(2)}] {_K('default')}: {_D(1)})",
        )

    def test_corgy_help_formatter_handles_conflicting_text_in_choice(self):
        with patch.object(CorgyHelpFormatter, "output_width", 200):
            self.assertEqual(
                self._get_arg_help(
                    "--x",
                    type=str,
                    choices=[
                        "a",
                        "b",
                        "--x str",
                        "['a'/\"b\"]",
                        "default: 'a'",
                        "--x str  x help (['a'/\"b\"] default: 'a')",
                    ],
                    default="a",
                    help="x help",
                ),
                # This is awful.
                #   --x str  x help ([
                f"  {_O('--x')} {_M('str')}  x help (["
                # a/b/
                + _C("a") + "/" + _C("b") + "/"
                # --x str/
                + _C("--x") + " " + _C("str") + "/"
                # ['a'/"b"]/
                + _C("['a'/\"b\"]") + "/"
                # default: 'a'/
                + _C("default:") + " " + _C("'a'") + "/"
                # --x str  x help
                + _C("--x") + " " + _C("str") + "  " + _C("x") + " " + _C("help")
                #  (['a'/"b"]
                + " " + _C("(['a'/\"b\"]")
                #  default: 'a')}]
                + " " + _C("default:") + " " + _C("'a')") + "] "
                # default: a
                + f"{_K('default')}: {_D('a')})",
            )

    def test_corgy_help_formatter_handles_long_choice(self):
        with patch.multiple(CorgyHelpFormatter, output_width=15, max_help_position=5):
            self.assertEqual(
                self._get_arg_help(
                    "--x",
                    type=str,
                    choices=["a", "supercalifragilisticexpialidocious choice", "b"],
                    default="a",
                ),
                #   --x str
                #       ([a/super
                #       califragi
                #       listicexp
                #       ialidocio
                #       us
                #       choice/b]
                #       default:
                #       a)
                f"  {_O('--x')} {_M('str')}\n"
                f"      ([{_C('a')}/{_C('super')}\n"
                f"      {_C('califragi')}\n"
                f"      {_C('listicexp')}\n"
                f"      {_C('ialidocio')}\n"
                f"      {_C('us')}\n"
                f"      {_C('choice')}/{_C('b')}]\n"
                f"      {_K('default')}:\n"
                f"      {_D('a')})",
            )

    def test_corgy_help_formatter_handles_default_suppress(self):
        self.assertEqual(
            self._get_arg_help("--arg", type=str, default=argparse.SUPPRESS),
            f"  {_O('--arg')} {_M('str')}  ({_K('optional')})",
        )

    def test_corgy_help_formatter_uses_name_for_choices(self):
        class A:
            ...

        self.assertEqual(
            self._get_arg_help("--arg", choices=[A]),
            f"  {_O('--arg')}  ([{_C('A')}] {_DNone()})",
        )

    def test_corgy_help_formatter_uses_name_for_default(self):
        class A:
            ...

        self.assertEqual(
            self._get_arg_help("--arg", default=A),
            f"  {_O('--arg')}  ({_K('default')}: {_D('A')})",
        )

    def test_corgy_help_formatter_uses_custom_choice_strs(self):
        class A:
            def __init__(self, x):
                self.x = x

            def __repr__(self):
                return f"A:{self.x}"

        self.assertEqual(
            self._get_arg_help("--arg", type=A, choices=[A(1), A("a")]),
            f"  {_O('--arg')} {_M('A')}  ([{_C('A:1')}/{_C('A:a')}] " f"{_DNone()})",
        )

    def test_corgy_help_formatter_handles_dict_default(self):
        class T(KeyValuePairs[str, int]):  # type: ignore[misc]
            @classmethod
            def _metavar(cls) -> str:
                return "T"

        self.assertEqual(
            self._get_arg_help("--x", type=T, default=T("a=1,b=2")),
            f"  {_O('--x')} {_M('T')}  ({_K('default')}: " f"{_D({'a': 1, 'b': 2})})",
        )

    def test_corgy_help_formatter_handles_dict_choices(self):
        class T(KeyValuePairs[str, int]):  # type: ignore[misc]
            @classmethod
            def _metavar(cls) -> str:
                return "T"

        _choices_str = "".join(
            (
                _C("{'a':"),
                " ",
                _C("1}"),
                "/",
                _C("{'b':"),
                " ",
                _C("2,"),
                " ",
                _C("'c':"),
                " ",
                _C("3}"),
            )
        )
        self.assertEqual(
            self._get_arg_help("--x", type=T, choices=(T("a=1"), T("b=2,c=3"))),
            f"  {_O('--x')} {_M('T')}  ([{_choices_str}] {_DNone()})",
        )


@skipIf(_CRAYONS is None, "`crayons` package not found")
class TestCorgyHelpFormatterMultiArgs(TestCase):
    def setUp(self):
        _COLOR_HELPER.crayons = _CRAYONS
        CorgyHelpFormatter.use_colors = True
        self.parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, usage=argparse.SUPPRESS
        )
        self.maxDiff = None

    def test_corgy_help_formatter_handles_multi_arg_alignment(self):
        self.parser.add_argument(
            "--x", type=int, help="x help", default=argparse.SUPPRESS
        )
        self.parser.add_argument("-y", "--why", type=float, required=True)
        self.parser.add_argument("-z", type=str, default="z", help="z help")

        self.assertEqual(
            self.parser.format_help(),
            # options:
            #   -h/--help       show this help message and exit
            #   --x int         x help (optional)
            #   -y/--why float  (required)
            #   -z str          z help (default: z)
            f"options:\n"
            f"  {_O('-h')}/{_O('--help')}       show this help message and exit\n"
            f"  {_O('--x')} {_M('int')}         x help ({_K('optional')})\n"
            f"  {_O('-y')}/{_O('--why')} {_M('float')}  ({_K('required')})\n"
            f"  {_O('-z')} {_M('str')}          z help ({_K('default')}: {_D('z')})\n",
        )

    def test_corgy_help_formatter_handles_multi_arg_wrapping(self):
        self.parser.add_argument(
            "-x", "--ex", type=float, help="help" * 10, default=argparse.SUPPRESS
        )
        with patch.object(CorgyHelpFormatter, "output_width", 30):
            self.assertEqual(
                self.parser.format_help(),
                # options:
                #   -h/--help      show this
                #                  help message
                #                  and exit
                #   -x/--ex float  helphelphelph
                #                  elphelphelphe
                #                  lphelphelphel
                #                  p (optional)
                f"options:\n"
                f"  {_O('-h')}/{_O('--help')}      show this\n"
                f"                 help message\n"
                f"                 and exit\n"
                f"  {_O('-x')}/{_O('--ex')} {_M('float')}  helphelphelph\n"
                f"                 elphelphelphe\n"
                f"                 lphelphelphel\n"
                f"                 p ({_K('optional')})\n",
            )

    def test_corgy_help_formatter_handles_multi_arg_with_small_max_help_pos(self):
        self.parser.add_argument("-x", "--ex", type=float, help="help" * 10)
        with patch.object(CorgyHelpFormatter, "max_help_position", 10):
            self.assertEqual(
                self.parser.format_help(),
                # options:
                #   -h/--help
                #       show this help message and exit
                #   -x/--ex float
                #       helphelphelphelphelphelphelphelphelphelp (optional)
                f"options:\n"
                f"  {_O('-h')}/{_O('--help')}\n"
                f"      show this help message and exit\n"
                f"  {_O('-x')}/{_O('--ex')} {_M('float')}\n"
                f"      helphelphelphelphelphelphelphelphelphelp ({_DNone()})\n",
            )

    def test_corgy_help_formatter_handles_argument_groups(self):
        self.parser.add_argument("arg", help="arg help")
        self.parser.add_argument("--x", type=str, help="x help")
        grp_parser = self.parser.add_argument_group("group 1")
        grp_parser.add_argument("--y", required=True)
        grp_parser.add_argument("--z", type=float)
        grp_parser = self.parser.add_argument_group("group 2", "group 2 description")
        grp_parser.add_argument("--w", type=str, default=argparse.SUPPRESS)

        self.assertEqual(
            self.parser.format_help(),
            # positional arguments:
            #   arg        arg help
            #
            # options:
            #   -h/--help  show this help message and exit
            #   --x str    x help (default: None)
            #
            # group 1:
            #   --y        (required)
            #   --z float  (default: None)
            #
            # group 2:
            #   group 2 description
            #   --w str    (optional)
            f"positional arguments:\n"
            f"  {_O('arg')}        arg help\n"
            f"\n"
            f"options:\n"
            f"  {_O('-h')}/{_O('--help')}  show this help message and exit\n"
            f"  {_O('--x')} {_M('str')}    x help ({_DNone()})\n"
            f"\n"
            f"group 1:\n"
            f"  {_O('--y')}        ({_K('required')})\n"
            f"  {_O('--z')} {_M('float')}  ({_DNone()})\n"
            f"\n"
            f"group 2:\n"
            f"  group 2 description\n"
            f"\n"
            f"  {_O('--w')} {_M('str')}    ({_K('optional')})\n",
        )

    def test_corgy_help_formatter_handles_sub_parsers(self):
        self.parser.add_argument("--arg", type=str)
        subparsers = self.parser.add_subparsers(help="sub commands")
        subparsers.add_parser("x", formatter_class=CorgyHelpFormatter)
        subparsers.add_parser("y", formatter_class=CorgyHelpFormatter)

        self.assertEqual(
            self.parser.format_help(),
            # positional arguments:
            #   CMD        sub commands ([x/y])
            #
            # options:
            #   -h/--help  show this help message and exit
            #   --arg str  (default: None)
            f"positional arguments:\n"
            f"  {_O('CMD')}        sub commands ([{_C('x')}/{_C('y')}])\n"
            f"\n"
            f"options:\n"
            f"  {_O('-h')}/{_O('--help')}  show this help message and exit\n"
            f"  {_O('--arg')} {_M('str')}  ({_DNone()})\n",
        )


@skipIf(_CRAYONS is None, "`crayons` package not found")
class TestCorgyHelpFormatterWithCorgyAnnotations(TestCase):
    def setUp(self):
        _COLOR_HELPER.crayons = _CRAYONS
        CorgyHelpFormatter.use_colors = True

    def _get_help_for_corgy_cls(self, corgy_cls):
        _parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )
        corgy_cls.add_args_to_parser(_parser)
        _help = _parser.format_help()
        if _help:
            return _help.split("\n", maxsplit=1)[1].rstrip()
        return ""

    def test_corgy_help_formatter_handles_sequence_of_optionals(self):
        class C(Corgy):
            x: Tuple[Optional[int], ...]

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [{_M('int')}] [[{_M('int')}] ...]  ({_K('optional')})",
        )

    def test_corgy_help_formatter_handles_sequence_of_strings(self):
        class C(Corgy):
            x: Sequence[str] = ["asdf", "g", "hj"]

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [{_M('str')} ...]  ({_K('default')}: "
            f"{_D('[asdf, g, hj]')})",
        )

    def test_corgy_help_formatter_handles_sequence_of_sequences(self):
        class C(Corgy):
            x: Tuple[Tuple[int, ...], ...]

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} {_M('int')} [{_M('int')} ...] "
            f"[{_M('int')} [{_M('int')} ...] ...]  ({_K('optional')})",
        )

    def test_corgy_help_formatter_handles_zero_or_more_sequences(self):
        class C(Corgy):
            x: Sequence[Sequence[int]]

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [[{_M('int')} ...] ...]  ({_K('optional')})",
        )

    def test_corgy_help_formatter_handles_fixed_sequence_of_sequences(self):
        class C(Corgy):
            x: Tuple[
                Tuple[Optional[int], ...],
                Tuple[Optional[int], ...],
                Tuple[Optional[int], ...],
            ]

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [{_M('int')}] [[{_M('int')}] ...] "
            f"[{_M('int')}] [[{_M('int')}] ...] [{_M('int')}] [[{_M('int')}] ...]  "
            f"({_K('optional')})",
        )

    def test_corgy_help_formatter_handles_nested_sequence_of_custom_types(self):
        class T:
            __metavar__ = "custom type"

        class C(Corgy):
            x: Tuple[T, ...]

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} {_M('custom')} {_M('type')} "
            f"[{_M('custom')} {_M('type')} ...]  ({_K('optional')})",
        )

    def test_corgy_help_formatter_handles_custom_type_sequence_default_value(self):
        class T:
            def __init__(self, s):
                self.s = s

            def __str__(self):
                return "T" + self.s

        class C(Corgy):
            x: Sequence[T] = [T("1"), T("2"), T("3")]

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [{_M('T')} ...]  ({_K('default')}: "
            f"{_D('[T1, T2, T3]')})",
        )

    def test_corgy_help_formatter_handles_custom_type_tuple_default_value(self):
        class T:
            def __init__(self, s):
                self.s = s

            def __str__(self):
                return "T" + self.s

        class C(Corgy):
            x: Tuple[T, ...] = (T("1"), T("2"), T("3"))

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} {_M('T')} [{_M('T')} ...]  ({_K('default')}: "
            f"{_D('(T1, T2, T3)')})",
        )

    def test_corgy_help_formatter_handles_tuple_default_for_sequence_type(self):
        class C(Corgy):
            x: Sequence[int] = (1, 2)

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [{_M('int')} ...]  ({_K('default')}: " f"{_D('(1, 2)')})",
        )

    def test_corgy_help_formatter_handles_default_of_optional_sequence(self):
        class T:
            def __init__(self, s):
                self.s = s

            def __str__(self):
                return "T" + self.s

        class C(Corgy):
            x: Tuple[Optional[T], ...] = (T("1"), None, T("2"))

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [{_M('T')}] [[{_M('T')}] ...]  ({_K('default')}: "
            f"{_D('(T1, None, T2)')})",
        )

    def test_corgy_help_formatter_handles_default_of_nested_tuples(self):
        class T:
            def __init__(self, s):
                self.s = s

            def __str__(self):
                return "T" + self.s

        class C(Corgy):
            x: Tuple[Tuple[Optional[T], ...], ...] = ((T("1"), None), (None, T("2")))

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [{_M('T')}] [[{_M('T')}] ...] "
            f"[[{_M('T')}] [[{_M('T')}] ...] ...]  ({_K('default')}: "
            f"{_D('((T1, None), (None, T2))')})",
        )

    def test_corgy_help_formatter_handles_default_of_nested_sequences(self):
        class T:
            def __init__(self, s):
                self.s = s

            def __str__(self):
                return "T" + self.s

        class C(Corgy):
            x: Sequence[Sequence[Optional[T]]] = ([T("1"), None], (None, T("2")))

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} [[[{_M('T')}] ...] ...]  ({_K('default')}: "
            f"{_D('([T1, None], (None, T2))')})",
        )

    def test_corgy_help_formatter_handles_directly_added_bare_sequence(self):
        _parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )
        _parser.add_argument("--x", type=Sequence, required=True)
        _help = _parser.format_help()
        if _help:
            _help = _help.split("\n", maxsplit=1)[1].rstrip()

        _tname = "typing.Sequence" if sys.version_info < (3, 9) else "Sequence"
        self.assertEqual(_help, f"  {_O('--x')} {_M(_tname)}  ({_K('required')})")

    def test_corgy_help_formatter_handles_directly_added_heterogenous_tuple(self):
        _T = Tuple[int, str, float]
        _parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )
        _parser.add_argument("--x", type=_T, required=True)
        _help = _parser.format_help()
        if _help:
            _help = _help.split("\n", maxsplit=1)[1].rstrip()

        self.assertEqual(
            _help,
            f"  {_O('--x')} {_M('int')} {_M('str')} {_M('float')}"
            f"  ({_K('required')})",
        )

    def test_corgy_help_formatter_handles_default_of_directly_added_het_tuple(self):
        class _TBase:
            def __init__(self, s):
                self.s = s

            def __str__(self):
                return f"{self.__class__.__name__}{self.s}"

        class T1(_TBase):
            ...

        class T2(_TBase):
            ...

        class T3(_TBase):
            ...

        _T = Tuple[T1, T2, T3]
        _parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )
        _parser.add_argument("--x", type=_T, default=(T1(1), T2(2), T3(3)))
        _help = _parser.format_help()
        if _help:
            _help = _help.split("\n", maxsplit=1)[1].rstrip()

        self.assertEqual(
            _help,
            f"  {_O('--x')} {_M('T1')} {_M('T2')} {_M('T3')}"
            f"  ({_K('default')}: {_D('(T11, T22, T33)')})",
        )

        _parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )
        _parser.add_argument("--x", type=_T, default=(T1(1), T2(2)))
        with self.assertRaises(ValueError):
            _parser.format_help()

    def test_corgy_help_formatter_handles_seq_default_for_non_seq_type(self):
        class T:
            def __init__(self, s):
                self.s = s

            def __str__(self):
                return "T" + self.s

        _parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )
        _parser.add_argument("--x", type=T, default=[T("1"), T("2")])
        _help = _parser.format_help()
        if _help:
            _help = _help.split("\n", maxsplit=1)[1].rstrip()

        self.assertEqual(
            _help, f"  {_O('--x')} {_M('T')}  ({_K('default')}: {_D('[T1, T2]')})"
        )

    def test_corgy_help_formatter_handles_required_attrs(self):
        class C(Corgy):
            x: Required[int]
            y: Required[int] = 1

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} {_M('int')}  ({_K('required')})\n"
            f"  {_O('--y')} {_M('int')}  ({_K('default')}: {_D('1')})",
        )

    def test_corgy_help_formatter_handles_not_required_attrs(self):
        class C(Corgy):
            x: NotRequired[int]
            y: NotRequired[int] = 1

        self.assertEqual(
            self._get_help_for_corgy_cls(C),
            f"  {_O('--x')} {_M('int')}  ({_K('optional')})\n"
            f"  {_O('--y')} {_M('int')}  ({_K('default')}: {_D('1')})",
        )


class TestCorgyHelpFormatterUsage(TestCase):
    def setUp(self):
        self.parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, prog=""
        )

    def test_corgy_help_formatter_usage_with_positional_arg(self):
        self.parser.add_argument("arg", type=int)
        self.assertEqual(
            self.parser.format_usage(),
            # usage: arg
            "usage: arg\n",
        )

    def test_corgy_help_formatter_usage_with_required_arg(self):
        self.parser.add_argument("--arg", type=str, required=True)
        self.assertEqual(
            self.parser.format_usage(),
            # usage: --arg str
            "usage: --arg str\n",
        )

    def test_corgy_help_formatter_usage_with_optional_arg(self):
        self.parser.add_argument("--arg", type=str)
        self.assertEqual(
            self.parser.format_usage(),
            # usage: [--arg str]
            "usage: [--arg str]\n",
        )

    def test_corgy_help_formatter_usage_with_group(self):
        self.parser.add_argument("--arg", type=str)
        grp_parser = self.parser.add_argument_group("grp")
        grp_parser.add_argument("--grp:arg", type=str)
        self.assertEqual(
            self.parser.format_usage(),
            # usage: [--arg str] [--grp:arg str]
            "usage: [--arg str] [--grp:arg str]\n",
        )

    def test_corgy_help_formatter_usage_with_choices(self):
        self.parser.add_argument("--arg", type=int, choices=(1, 2))
        self.assertEqual(
            self.parser.format_usage(),
            # usage: [--arg int]
            "usage: [--arg int]\n",
        )

    def test_corgy_help_formatter_always_shows_usage_when_called_explicitly(self):
        with patch.object(CorgyHelpFormatter, "show_full_help", False):
            self.parser.add_argument("--arg", type=str)
            self.assertEqual(
                self.parser.format_usage(),
                # usage: [--arg str]
                "usage: [--arg str]\n",
            )
            self.assertEqual(
                self.parser.format_help(),
                # options:
                #   --arg str  (default: None)
                f"options:\n" f"  {_O('--arg')} {_M('str')}  ({_DNone()})\n",
            )


class _NoColorTestMeta(type):
    """Metaclass to create versions of test classes that don't use colors."""

    def __new__(cls, name, bases, namespace, **kwds):  # pylint: disable=duplicate-code
        for _item in dir(bases[0]):
            if not _item.startswith("test_"):
                continue
            test_fn = getattr(bases[0], _item)
            new_test_fn_name = f"{_item}_no_color"
            namespace[new_test_fn_name] = test_fn

        bases = (TestCase,)  # to prevent duplication of tests in the base class
        return super().__new__(cls, name, bases, namespace, **kwds)


class TestCorgyHelpFormatterSingleArgsNoColor(
    TestCorgyHelpFormatterSingleArgs, metaclass=_NoColorTestMeta
):
    # The metaclass removes the base class from the inheritance chain, so we need to
    # manually inherit needed base class methods.
    _get_arg_help = TestCorgyHelpFormatterSingleArgs._get_arg_help

    def setUp(self):
        _COLOR_HELPER.crayons = None
        CorgyHelpFormatter.use_colors = False
        self.parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, add_help=False, usage=argparse.SUPPRESS
        )


class TestCorgyHelpFormatterMultiArgsNoColor(
    TestCorgyHelpFormatterMultiArgs, metaclass=_NoColorTestMeta
):
    def setUp(self):
        _COLOR_HELPER.crayons = None
        CorgyHelpFormatter.use_colors = False
        self.parser = ArgumentParser(
            formatter_class=CorgyHelpFormatter, usage=argparse.SUPPRESS
        )


class TestCorgyHelpFormatterWithCorgyAnnotationsNoColor(
    TestCorgyHelpFormatterWithCorgyAnnotations, metaclass=_NoColorTestMeta
):
    _get_help_for_corgy_cls = (
        TestCorgyHelpFormatterWithCorgyAnnotations._get_help_for_corgy_cls
    )

    def setUp(self):
        _COLOR_HELPER.crayons = None
        CorgyHelpFormatter.use_colors = False
