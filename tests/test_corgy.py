import argparse
import unittest
from collections.abc import Sequence
from typing import Annotated, Literal, Optional, Sequence as SequenceType
from unittest.mock import MagicMock, patch

import corgy
from corgy import Corgy, CorgyHelpFormatter, corgyparser


class TestCorgyMeta(unittest.TestCase):
    """Tests to check validity of classes inheriting from Corgy."""

    # pylint: disable=unused-variable, unused-private-member

    class _CorgyCls(Corgy):
        x1: Sequence[int]
        x2: Annotated[int, "x2 docstr"]
        x3: int = 3
        x4: Annotated[str, "x4 docstr"] = "4"

    def test_corgy_cls_has_properties_from_type_hints(self):
        for _x in ["x1", "x2", "x3", "x4"]:
            with self.subTest(var=_x):
                self.assertTrue(hasattr(self._CorgyCls, _x))
                self.assertIsInstance(getattr(self._CorgyCls, _x), property)

    def test_corgy_instance_returns_correct_defaults(self):
        corgy_inst = self._CorgyCls()
        for _x, _d in zip(["x3", "x4"], [3, "4"]):
            with self.subTest(var=_x):
                _x_default = getattr(corgy_inst, _x)
                self.assertEqual(_x_default, _d)

    def test_corgy_instance_raises_on_unset_attr_access_without_default(self):
        corgy_inst = self._CorgyCls()
        for _x in ["x1", "x2"]:
            with self.subTest(var=_x):
                with self.assertRaises(AttributeError):
                    _x_default = getattr(corgy_inst, _x)

    def test_corgy_cls_adds_hint_metadata_as_property_docstrings(self):
        for _x in ["x1", "x2", "x3", "x4"]:
            with self.subTest(var=_x):
                _x_prop = getattr(self._CorgyCls, _x)
                if _x in ["x1", "x3"]:
                    self.assertIsNone(_x_prop.__doc__)
                else:
                    self.assertEqual(_x_prop.__doc__, f"{_x} docstr")

    def test_corgy_cls_properties_have_correct_type_annotations(self):
        for _x, _type in zip(["x1", "x2", "x3", "x4"], [Sequence[int], int, int, str]):
            with self.subTest(var=_x):
                _x_prop = getattr(self._CorgyCls, _x)
                self.assertEqual(_x_prop.fget.__annotations__["return"], _type)

                self.assertEqual(
                    len(_x_prop.fget.__annotations__),
                    1,
                    f"spurious annotations: {_x_prop.fget.__annotations__}",
                )

                self.assertEqual(_x_prop.fset.__annotations__["val"], _type)
                self.assertEqual(
                    len(_x_prop.fset.__annotations__),
                    1,
                    f"spurious annotations: {_x_prop.fset.__annotations__}",
                )

    def test_corgy_cls_raises_if_help_annotation_not_str(self):
        with self.assertRaises(TypeError):

            class C1(Corgy):
                x: Annotated[int, 1]

    def test_corgy_cls_uses_only_frist_element_of_variadic_annotation(self):
        class C2(Corgy):
            x: Annotated[int, "x help", "blah", 3]

        self.assertEqual(C2.x.__doc__, "x help")

    def test_corgy_cls_allows_dunder_defaults_as_var_name(self):
        class C(Corgy):
            __defaults: int
            x: int = 0

        self.assertTrue(hasattr(C, "__defaults"))
        self.assertIsInstance(getattr(C, "__defaults"), dict)
        self.assertTrue(hasattr(C, "_C__defaults"))
        self.assertIsInstance(getattr(C, "_C__defaults"), property)
        self.assertEqual(C().x, 0)

    def test_corgy_cls_raises_if_var_name_is_dunder_another_var(self):
        with self.assertRaises(TypeError):

            class C1(Corgy):
                x: int = 0
                __x = 2

        with self.assertRaises(TypeError):

            class C2(Corgy):
                x: int
                __x: int

    def test_corgy_cls_can_have_dunder_name(self):
        self.assertTrue(hasattr(self._CorgyCls, "_CorgyCls__x1"))

        class __C(Corgy):
            x: int

        self.assertTrue(hasattr(__C, "_C__x"))
        c = __C()
        c.x = 3
        self.assertEqual(c.x, 3)

    def test_corgy_cls_raises_on_setting_undefined_attribute(self):
        c = self._CorgyCls()
        with self.assertRaises(AttributeError):
            c.z = 0

    def test_corgy_cls_has_correct_repr(self):
        c = self._CorgyCls()
        c.x1 = [0, 1]
        c.x2 = 2
        c.x4 = "8"
        self.assertEqual(str(c), "_CorgyCls(x1=[0, 1], x2=2, x3=3, x4='8')")

    def test_corgy_cls_repr_handles_unset_values(self):
        c = self._CorgyCls()
        self.assertEqual(str(c), "_CorgyCls(x1=<unset>, x2=<unset>, x3=3, x4='4')")


class TestCorgyAddArgsToParser(unittest.TestCase):
    """Tests to check that Corgy properly adds arguments to ArgumentParsers."""

    def setUp(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument = MagicMock()
        self.parser.add_argument_group = MagicMock()

    def test_add_args_replaces_underscores_with_hyphens(self):
        class C(Corgy):
            the_x_arg: int

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--the-x-arg", type=int, required=True
        )

    def test_add_args_handles_provided_prefix(self):
        class C(Corgy):
            the_x_arg: int

        C.add_args_to_parser(self.parser, "prefix")
        self.parser.add_argument.assert_called_once_with(
            "--prefix:the-x-arg", type=int, required=True
        )

    def test_add_args_handles_plain_type_annotation(self):
        class C(Corgy):
            x: int

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, required=True)

    def test_add_args_handles_default_value(self):
        class C(Corgy):
            x: int = 0

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, default=0)

    def test_add_args_handles_annotated_optional(self):
        class C(Corgy):
            x: Optional[int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int)

    def test_add_args_handles_annotated_optional_with_default(self):
        class C(Corgy):
            x: Optional[int] = 0

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, default=0)

    def test_add_args_allows_incorrectly_typed_default(self):
        class C(Corgy):
            x: int = "x"

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, default="x")

    def test_add_args_uses_metadata_as_help(self):
        class C(Corgy):
            x: Annotated[int, "x docstring"]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, required=True, help="x docstring"
        )

    def test_add_args_converts_literal_to_choices(self):
        class C(Corgy):
            x: Literal[1, 2, 3]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, required=True, choices=(1, 2, 3)
        )

    def test_add_args_raises_if_choices_not_same_type(self):
        class C(Corgy):
            x: Literal[1, 2, "3"]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    def test_add_args_handles_user_defined_class_as_type(self):
        class T:
            pass

        class C(Corgy):
            x: T

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=T, required=True)

    def test_add_args_handles_user_defined_object_as_default(self):
        class T:
            pass

        t = T()

        class C(Corgy):
            x: T = t

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=T, default=t)

    def test_add_args_converts_bool_to_action(self):
        class C(Corgy):
            x: bool

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, action=argparse.BooleanOptionalAction, required=True
        )

    def test_add_args_handles_default_for_bool_type(self):
        class C(Corgy):
            x: bool = False

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, action=argparse.BooleanOptionalAction, default=False
        )

    def test_add_args_does_not_convert_bool_sequence_to_action(self):
        class C(Corgy):
            x: Sequence[bool]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, required=True, nargs="*"
        )

    def test_add_args_sets_nargs_to_asterisk_for_sequence_type(self):
        class C(Corgy):
            x: Sequence[int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs="*", required=True
        )

    def test_add_args_handles_sequence_type_as_well_as_abstract_sequence(self):
        class C(Corgy):
            x: SequenceType[int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs="*", required=True
        )

    def test_add_args_handles_optional_sequence_type(self):
        class C(Corgy):
            x: Optional[Sequence[int]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, nargs="*")

    def test_add_args_sets_nargs_to_plus_for_non_empty_sequence_type(self):
        class C(Corgy):
            x: Sequence[int, ...]  # type: ignore

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs="+", required=True
        )

    def test_add_args_handles_sequence_with_default(self):
        class C(Corgy):
            x: Sequence[int] = [1, 2, 3]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs="*", default=[1, 2, 3]
        )

    def test_add_args_converts_literal_sequence_to_choices_with_nargs(self):
        class C(Corgy):
            x: Sequence[Literal[1, 2, 3]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs="*", required=True, choices=(1, 2, 3)
        )

    def test_add_args_handles_fixed_length_sequence_with_chocies(self):
        class C(Corgy):
            x: Sequence[Literal[1, 2, 3], Literal[1, 2, 3]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs=2, required=True, choices=(1, 2, 3)
        )

    def test_add_args_raises_if_fixed_length_sequence_choices_not_all_same(self):
        class C(Corgy):
            x: Sequence[Literal[1, 2, 3], Literal[1, 2]]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    def test_add_args_handles_fixed_length_typed_sequence(self):
        class C(Corgy):
            x: Sequence[int, int, int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs=3, required=True
        )

    def test_add_args_handles_length_2_typed_sequence(self):
        class C(Corgy):
            x: Sequence[int, int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs=2, required=True
        )

    def test_add_args_raises_if_fixed_length_sequence_types_not_all_same(self):
        class C(Corgy):
            x: Sequence[int, str, int]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    def test_add_args_converts_corgy_var_to_argument_group(self):
        class G(Corgy):
            x: int

        G.add_args_to_parser = MagicMock()

        class C(Corgy):
            g: Annotated[G, "group G"]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument_group.assert_called_once_with("g", "group G")
        G.add_args_to_parser.assert_called_once_with(
            self.parser.add_argument_group.return_value, "g"
        )

    def test_add_args_allows_repeated_name_in_group(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, required=True)
        self.parser.add_argument_group.assert_called_once_with("g", None)

    def test_add_args_infers_correct_base_type_from_complex_type_hint(self):
        class C(Corgy):
            x: Annotated[Optional[Sequence[str]], "x"]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=str, help="x", nargs="*"
        )

    def test_add_args_raises_if_base_type_is_optional(self):
        class C(Corgy):
            x: Sequence[Optional[int]]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    def test_add_args_raises_if_base_type_not_valid(self):
        class C(Corgy):
            x: Sequence["int"]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    def test_add_args_raises_if_base_type_generic(self):
        class C(Corgy):
            x: Annotated[list[str], "x"]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    def test_add_args_allows_list_base_type(self):
        class C(Corgy):
            x: Annotated[list, "x"]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=list, required=True, help="x"
        )


class TestCorgyCmdlineParsing(unittest.TestCase):
    """Test cases to check parsing of command line arguments by Corgy."""

    def setUp(self):
        self.parser = argparse.ArgumentParser()
        self.orig_parse_args = argparse.ArgumentParser.parse_args

    def test_cmdline_args_are_parsed_to_corgy_cls_properties(self):
        class C(Corgy):
            x: int
            y: str
            z: Sequence[int]

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "1", "--y", "2", "--z", "3", "4"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.x, 1)
        self.assertEqual(c.y, "2")
        self.assertListEqual(c.z, [3, 4])

    def test_cmdline_parsing_handles_group_arguments(self):
        class G(Corgy):
            x: int
            y: str

        class C(Corgy):
            x: int
            y: int
            g: G

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "1", "--y", "2", "--g:x", "3", "--g:y", "four"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.x, 1)
        self.assertEqual(c.y, 2)
        self.assertEqual(c.g.x, 3)
        self.assertEqual(c.g.y, "four")

    def test_cmdline_parsing_handles_nested_groups(self):
        class G1(Corgy):
            x: int

        class G2(Corgy):
            x: int
            g: G1

        class C(Corgy):
            x: int
            g1: G1
            g2: G2

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "1", "--g1:x", "2", "--g2:x", "3", "--g2:g:x", "4"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.x, 1)
        self.assertEqual(c.g1.x, 2)
        self.assertEqual(c.g2.x, 3)
        self.assertEqual(c.g2.g.x, 4)

    def test_cmdline_parsing_handles_list_base_type(self):
        class C(Corgy):
            x: list

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "123"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertListEqual(c.x, ["1", "2", "3"])

    def test_cmdline_parsing_handles_custom_base_type(self):
        class A:
            def __init__(self, s):
                x, y = s.split(",")
                self.x = int(x)
                self.y = float(y)

        class C(Corgy):
            a: A

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--a", "1,2.3"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.a.x, 1)
        self.assertEqual(c.a.y, 2.3)

    def test_parse_from_cmdline_passes_extra_args_to_parser_constructor(self):
        class C(Corgy):
            x: int

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["--x", "1"])
        with patch(
            "corgy.corgy.argparse.ArgumentParser", MagicMock(return_value=self.parser)
        ):
            C.parse_from_cmdline(
                formatter_class=argparse.ArgumentDefaultsHelpFormatter, add_help=False
            )
            corgy.corgy.argparse.ArgumentParser.assert_called_once_with(
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                add_help=False,
            )

    def test_parse_from_cmdline_uses_corgy_help_formatter_if_no_formatter_specified(
        self,
    ):
        class C(Corgy):
            x: int

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["--x", "1"])
        with patch(
            "corgy.corgy.argparse.ArgumentParser", MagicMock(return_value=self.parser)
        ):
            C.parse_from_cmdline(add_help=False)
            corgy.corgy.argparse.ArgumentParser.assert_called_once_with(
                formatter_class=CorgyHelpFormatter, add_help=False
            )


class TestCorgyCustomParsers(unittest.TestCase):
    """Tests to check usage of the @corgyparser decorator."""

    # pylint: disable=no-self-argument, unused-variable

    def test_corgyparser_raises_if_not_passed_name(self):
        with self.assertRaises(TypeError):

            @corgyparser
            def spam():
                pass

    def test_corgy_raises_if_corgyparser_target_invalid(self):
        with self.assertRaises(TypeError):

            class A(Corgy):
                x: int

                @corgyparser("y")
                def parsex(s: str):  # type: ignore
                    return 0

    def test_add_args_handles_corgyparser(self):
        class C(Corgy):
            x: Annotated[int, "x"]

            @corgyparser("x")
            def parsex(s: str):  # type: ignore
                return 0

        parser = argparse.ArgumentParser()
        parser.add_argument = MagicMock()
        C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x", type=getattr(C, "__parsers")["x"], required=True, help="x"
        )

    def test_add_args_with_custom_parser_respects_default_value(self):
        class C(Corgy):
            x: int = 1

            @corgyparser("x")
            def parsex(s: str):  # type: ignore
                return 0

        parser = argparse.ArgumentParser()
        parser.add_argument = MagicMock()
        C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x", type=getattr(C, "__parsers")["x"], default=1
        )

    def test_cmdline_parsing_calls_custom_parser(self):
        class C(Corgy):
            x: int

            @corgyparser("x")
            def parsex(s: str):  # type: ignore
                return 0

        getattr(C, "__parsers")["x"] = MagicMock()
        parser = argparse.ArgumentParser()
        orig_parse_args = argparse.ArgumentParser.parse_args
        parser.parse_args = lambda: orig_parse_args(parser, ["--x", "test"])

        C.parse_from_cmdline(parser)
        getattr(C, "__parsers")["x"].assert_called_once_with("test")

    def test_cmdline_parsing_returns_custom_parser_output(self):
        class C(Corgy):
            x: int

            @corgyparser("x")
            def parsex(s: str):  # type: ignore
                return -1

        parser = argparse.ArgumentParser()
        orig_parse_args = argparse.ArgumentParser.parse_args
        parser.parse_args = lambda: orig_parse_args(parser, ["--x", "test"])

        args = C.parse_from_cmdline(parser)
        self.assertEqual(args.x, -1)
