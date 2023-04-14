import argparse
import sys
from argparse import ArgumentParser, ArgumentTypeError
from contextlib import redirect_stderr
from functools import partial
from io import StringIO
from typing import ClassVar, Optional, Tuple
from unittest import TestCase
from unittest.mock import MagicMock, patch

if sys.version_info >= (3, 9):
    from typing import Annotated, Literal
else:
    from typing_extensions import Annotated, Literal

from corgy import Corgy, corgyparser, Required
from corgy._corgyparser import CorgyParserAction


class TestCorgyCustomParsers(TestCase):
    def test_corgyparser_raises_if_not_passed_name(self):
        with self.assertRaises(TypeError):

            @corgyparser
            def spam():
                ...

    def test_corgy_raises_if_corgyparser_target_invalid(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int

                @corgyparser("y")
                def parsex(s):  # type: ignore # pylint: disable=no-self-argument
                    return 0

    def test_corgy_raises_if_corgyparser_target_not_annotated(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int
                y = 1

                @corgyparser("y")
                @staticmethod
                def parsex(s):
                    return 0

    def test_corgy_raises_if_corgyparser_target_classvar(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: ClassVar[int]

                @corgyparser("x")
                @staticmethod
                def parsex(s):
                    return 0

    def test_corgyparser_raises_on_nargs_mismatch(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int
                y: int

                @corgyparser("x")
                @corgyparser("y", nargs="+")
                @staticmethod
                def parsex(s):
                    return 0

        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int
                y: int

                @corgyparser("x", nargs=2)
                @corgyparser("y", nargs="*")
                @staticmethod
                def parsex(s):
                    return 0

    def test_add_args_handles_corgyparser(self):
        class C(Corgy):
            x: Annotated[int, "x"]

            @corgyparser("x")
            def parsex(s):  # type: ignore # pylint: disable=no-self-argument
                return 0

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        _parser_action = partial(CorgyParserAction, C.parsex)
        with patch("corgy._corgy.partial", MagicMock(return_value=_parser_action)):
            C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x", type=str, help="x", action=_parser_action, default=argparse.SUPPRESS
        )

    def test_add_args_with_custom_parser_respects_default_value(self):
        class C(Corgy):
            x: int = 1

            @corgyparser("x")
            def parsex(s):  # type: ignore # pylint: disable=no-self-argument
                return 0

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        _parser_action = partial(CorgyParserAction, C.parsex)
        with patch("corgy._corgy.partial", MagicMock(return_value=_parser_action)):
            C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x", type=str, default=1, action=_parser_action
        )

    def test_cmdline_parsing_calls_custom_parser(self):
        class C(Corgy):
            x: int

            @corgyparser("x")
            def parsex(s):  # type: ignore # pylint: disable=no-self-argument
                return 0

        getattr(C, "__parsers")["x"] = MagicMock(return_value=0)
        parser = ArgumentParser()
        orig_parse_args = ArgumentParser.parse_args
        parser.parse_args = lambda: orig_parse_args(parser, ["--x", "test"])

        C.parse_from_cmdline(parser)
        getattr(C, "__parsers")["x"].assert_called_once_with("test")

    def test_cmdline_parsing_calls_custom_parser_with_specified_nargs(self):
        orig_parse_args = ArgumentParser.parse_args

        def _run_and_check(cls, nargs, cmd_args, expected_call_args):
            getattr(cls, "__parsers")["x"] = MagicMock(return_value=0, __nargs__=nargs)
            parser = ArgumentParser()
            parser.parse_args = lambda: orig_parse_args(parser, ["--x"] + cmd_args)
            parser.error = MagicMock(side_effect=ArgumentTypeError)
            cls.parse_from_cmdline(parser)
            getattr(cls, "__parsers")["x"].assert_called_once_with(*expected_call_args)

        for nargs in [None, "*", "+", 3]:

            class C(Corgy):
                x: int

                @corgyparser("x", nargs=nargs)  # pylint: disable=cell-var-from-loop
                @staticmethod
                def parsex(s):
                    return 0

            if nargs is None:
                _run_and_check(C, nargs, ["x"], ["x"])
                # _run_and_check(C, [], [])
                with self.assertRaises(ArgumentTypeError):
                    _run_and_check(C, nargs, ["x", "y"], [["x", "y"]])
            elif nargs == "*":
                _run_and_check(C, nargs, ["x"], [["x"]])
                _run_and_check(C, nargs, [], [[]])
            elif nargs == "+":
                _run_and_check(C, nargs, ["x"], [["x"]])
                with self.assertRaises(ArgumentTypeError):
                    _run_and_check(C, nargs, [], [])
            else:
                _run_and_check(C, nargs, ["x", "y", "z"], [["x", "y", "z"]])
                with self.assertRaises(ArgumentTypeError):
                    _run_and_check(C, nargs, ["x", "y"], [["x", "y"]])

    def test_cmdline_parsing_returns_custom_parser_output(self):
        class C(Corgy):
            x: int

            @corgyparser("x")
            def parsex(s):  # type: ignore # pylint: disable=no-self-argument
                return -1

        parser = ArgumentParser()
        orig_parse_args = ArgumentParser.parse_args
        parser.parse_args = lambda: orig_parse_args(parser, ["--x", "test"])

        args = C.parse_from_cmdline(parser)
        self.assertEqual(args.x, -1)

    def test_corgyparser_allows_decorating_staticmethod(self):
        class C(Corgy):
            x: int

            @corgyparser("x")
            @staticmethod
            def parsex(s):
                return 0

        parser = ArgumentParser()
        orig_parse_args = ArgumentParser.parse_args
        parser.parse_args = lambda: orig_parse_args(parser, ["--x", "test"])

        c = C.parse_from_cmdline(parser)
        self.assertEqual(c.x, 0)

    def test_corgyparser_raises_if_decorating_non_staticmethod(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int

                @corgyparser("x")
                @classmethod
                def parsex(cls, s):
                    return 0

    def test_corgyparser_functions_are_callable(self):
        class C(Corgy):
            x: int
            y: int

            @corgyparser("x")
            @staticmethod
            def parsex(s):
                return 0

            @corgyparser("y")
            def parsey(s):  # type: ignore # pylint: disable=no-self-argument
                return 1

        self.assertEqual(C.parsex("x"), 0)
        self.assertEqual(C.parsey("y"), 1)

    def test_corgyparser_accepts_multiple_arguments(self):
        class C(Corgy):
            x: int
            y: int

            @corgyparser("x", "y")
            @staticmethod
            def parsexy(s):
                return 0

        self.assertIs(getattr(C, "__parsers")["x"], getattr(C, "__parsers")["y"])

    def test_corgyparser_decorators_can_be_chained(self):
        class C(Corgy):
            x: int
            y: int

            @corgyparser("x")
            @corgyparser("y")
            @staticmethod
            def parsexy(s):
                return 0

        self.assertIs(getattr(C, "__parsers")["x"], getattr(C, "__parsers")["y"])

    def test_corgyparser_allows_setting_metavar(self):
        class C(Corgy):
            x: int

            @corgyparser("x", metavar="custom")
            @staticmethod
            def parsex(s):
                return 0

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        _parser_action = partial(CorgyParserAction, C.parsex)
        with patch("corgy._corgy.partial", MagicMock(return_value=_parser_action)):
            C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x",
            type=str,
            action=_parser_action,
            default=argparse.SUPPRESS,
            metavar="custom",
        )

    def test_corgyparser_handles_setting_metavar_with_chaining(self):
        class C(Corgy):
            x: int
            y: int
            z: int
            w: int

            @corgyparser("x")
            @corgyparser("y", metavar="custom y")
            @corgyparser("z")
            @corgyparser("w", metavar="custom w")
            @staticmethod
            def parsexyzw(s):
                return 0

        self.assertEqual(C.parsexyzw.fparse.__metavar__, "custom y")

    def test_add_args_with_custom_parser_uses_custom_metavar(self):
        class T:
            __metavar__ = "T"

        class C(Corgy):
            x: T

            @corgyparser("x")
            @staticmethod
            def parsex(s):
                return 0

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        _parser_action = partial(CorgyParserAction, C.parsex)
        with patch("corgy._corgy.partial", MagicMock(return_value=_parser_action)):
            C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x",
            type=str,
            action=_parser_action,
            default=argparse.SUPPRESS,
            metavar="T",
        )

    def test_add_args_handles_bool_with_custom_parser(self):
        class C(Corgy):
            x: bool

            @corgyparser("x", nargs=2, metavar=("a", "b"))
            @staticmethod
            def parsex(s):
                return s[0] == s[1]

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        _parser_action = partial(CorgyParserAction, C.parsex)
        with patch("corgy._corgy.partial", MagicMock(return_value=_parser_action)):
            C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x",
            type=str,
            action=_parser_action,
            default=argparse.SUPPRESS,
            nargs=2,
            metavar=("a", "b"),
        )

    def test_corgyparser_metavar_overrides_type_metavar(self):
        class T:
            __metavar__ = "T"

        class C(Corgy):
            x: T

            @corgyparser("x", metavar="custom")
            @staticmethod
            def parsex(s):
                return 0

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        _parser_action = partial(CorgyParserAction, C.parsex)
        with patch("corgy._corgy.partial", MagicMock(return_value=_parser_action)):
            C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x",
            type=str,
            action=_parser_action,
            default=argparse.SUPPRESS,
            metavar="custom",
        )

    def test_corgy_cls_inherits_custom_parser(self):
        class C(Corgy):
            x: int

            @corgyparser("x")
            @staticmethod
            def parsex(s):
                return int(s[0]) + 1

        class D(C):
            ...

        parser = ArgumentParser()
        orig_parse_args = ArgumentParser.parse_args
        parser.parse_args = lambda: orig_parse_args(parser, ["--x", "1"])

        d = D.parse_from_cmdline(parser)
        self.assertEqual(d.x, 2)

    def test_corgy_cls_overrides_nargs_with_custom_parser(self):
        class C1(Corgy):
            x: Tuple[int]

            @corgyparser("x")
            @staticmethod
            def parsex(s):
                return 0

        class C2(C1):
            x: Tuple[int, ...]  # type: ignore

        class C3(C1):
            x: Tuple[int, int, int]  # type: ignore

        for C in (C1, C2, C3):
            with self.subTest(cls=C.__name__):
                parser = ArgumentParser()
                parser.add_argument = MagicMock()
                _parser_action = partial(CorgyParserAction, C.parsex)
                with patch(
                    "corgy._corgy.partial", MagicMock(return_value=_parser_action)
                ):
                    C.add_args_to_parser(parser)
                parser.add_argument.assert_called_once_with(
                    "--x", type=str, default=argparse.SUPPRESS, action=_parser_action
                )

    def test_corgy_cls_respects_choices_with_custom_parser(self):
        class C(Corgy):
            x: Literal[10, 20, 30]

            @corgyparser("x", nargs="+")
            @staticmethod
            def parsex(s):
                return sum(map(int, s))

        orig_parse_args = ArgumentParser.parse_args

        def _run_with_args(*cmd_args):
            with redirect_stderr(StringIO()):
                parser = ArgumentParser()
                parser.parse_args = lambda: orig_parse_args(
                    parser, ["--x"] + list(cmd_args)
                )
                args = C.parse_from_cmdline(parser)
                return args.x

        with self.assertRaises(SystemExit):
            _run_with_args("2", "3", "4")
        self.assertEqual(_run_with_args("1", "2", "3", "4"), 10)

    def test_corgy_cls_respects_optional_with_custom_parser(self):
        class C(Corgy):
            x: Optional[int]

            @corgyparser("x")
            @staticmethod
            def parsex(s):
                return 0

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        _parser_action = partial(CorgyParserAction, C.parsex)
        with patch("corgy._corgy.partial", MagicMock(return_value=_parser_action)):
            C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x", type=str, action=_parser_action, default=argparse.SUPPRESS
        )

    def test_cmdline_parsing_of_complex_nested_types_works_with_custom_parser(self):
        class C(Corgy):
            x: Tuple[Tuple[int, float], ...]

            @corgyparser("x", nargs="*")
            @staticmethod
            def parsex(s_tup):
                if not s_tup:
                    raise ValueError
                if len(s_tup) % 2:
                    raise ValueError
                o_list = []
                for _i in range(len(s_tup) // 2):
                    s = [s_tup[2 * _i], s_tup[2 * _i + 1]]
                    o_list.append((int(s[0]), float(s[1])))
                return tuple(o_list)

        orig_parse_args = ArgumentParser.parse_args

        def _run_with_args(*cmd_args):
            with redirect_stderr(StringIO()):
                parser = ArgumentParser()
                parser.parse_args = lambda: orig_parse_args(
                    parser, ["--x"] + list(cmd_args)
                )
                args = C.parse_from_cmdline(parser)
                return args.x

        self.assertTupleEqual(_run_with_args("1", "2.1"), ((1, 2.1),))
        self.assertTupleEqual(
            _run_with_args("1", "2.1", "3", "4.1"), ((1, 2.1), (3, 4.1))
        )
        with self.assertRaises(SystemExit):
            _run_with_args("1", "two")
        with self.assertRaises(SystemExit):
            _run_with_args("1.1", "2.1")
        with self.assertRaises(SystemExit):
            _run_with_args("1", "2.1", "3")
        with self.assertRaises(SystemExit):
            _run_with_args()

    def test_custom_parsers_handle_required_attrs(self):
        class C(Corgy):
            x: Required[int]

            @corgyparser("x")
            @staticmethod
            def parsex(s):
                return int(s)

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        _parser_action = partial(CorgyParserAction, C.parsex)
        with patch("corgy._corgy.partial", MagicMock(return_value=_parser_action)):
            C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x", type=str, action=_parser_action, required=True
        )
