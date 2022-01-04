import argparse
import sys
import unittest
from typing import Optional, Sequence
from unittest import skipIf
from unittest.mock import MagicMock, patch

SequenceType = Sequence

if sys.version_info >= (3, 9):
    from collections.abc import Sequence  # pylint: disable=reimported
    from typing import Annotated, Literal
else:
    from typing_extensions import Annotated

    if sys.version_info >= (3, 8):
        from typing import Literal
    else:
        from typing_extensions import Literal

import corgy
from corgy import Corgy, CorgyHelpFormatter, corgyparser
from corgy._corgy import BooleanOptionalAction


class TestCorgyMeta(unittest.TestCase):
    """Tests to check validity of classes inheriting from Corgy."""

    @classmethod
    def setUpClass(cls):
        class _CorgyCls(Corgy):
            x1: Sequence[int]
            x2: Annotated[int, "x2 docstr"]
            x3: int = 3
            x4: Annotated[str, "x4 docstr"] = "4"

        cls._CorgyCls = _CorgyCls

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

            class _(Corgy):
                x: Annotated[int, 1]

    def test_corgy_cls_raises_if_flags_not_list(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: Annotated[int, "x help", "x"]

    def test_corgy_cls_raises_if_flag_list_empty(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: Annotated[int, "x help", []]

    def test_add_args_raises_if_custom_flags_on_group(self):
        with self.assertRaises(TypeError):

            class G(Corgy):
                x: int

            class _(Corgy):
                g: Annotated[G, "group G", ["-g", "--grp"]]

    def test_corgy_cls_allows_dunder_defaults_as_var_name(self):
        class C(Corgy):
            __defaults: int  # pylint: disable=unused-private-member
            x: int = 0

        self.assertTrue(hasattr(C, "__defaults"))
        self.assertIsInstance(getattr(C, "__defaults"), dict)
        self.assertTrue(hasattr(C, "_C__defaults"))
        self.assertIsInstance(getattr(C, "_C__defaults"), property)
        self.assertEqual(C().x, 0)

    def test_corgy_cls_raises_if_var_name_is_dunder_another_var(self):
        with self.assertRaises(TypeError):

            class _C(Corgy):  # pylint: disable=unused-variable
                x: int = 0
                __x = 2  # pylint: disable=unused-private-member

        with self.assertRaises(TypeError):

            class _C(Corgy):  # pylint: disable=unused-variable
                x: int
                __x: int  # pylint: disable=unused-private-member

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

    def test_corgy_cls_allows_custom_slots(self):
        class C(Corgy):
            __slots__ = ("y",)
            x: int

        c = C()
        c.y = 1
        self.assertEqual(c.y, 1)

    def test_corgy_cls_has_correct_repr_str(self):
        c = self._CorgyCls()
        c.x1 = [0, 1]
        c.x2 = 2
        c.x4 = "8"
        self.assertEqual(repr(c), "_CorgyCls(x1=[0, 1], x2=2, x3=3, x4='8')")
        self.assertEqual(str(c), "_CorgyCls(x1=[0, 1], x2=2, x3=3, x4=8)")

    def test_corgy_cls_repr_handles_unset_values(self):
        c = self._CorgyCls()
        self.assertEqual(repr(c), "_CorgyCls(x1=<unset>, x2=<unset>, x3=3, x4='4')")

    def test_corgy_cls_repr_handles_groups(self):
        class D(Corgy):
            x: int
            c: self._CorgyCls

        d = D(x=1, c=self._CorgyCls(x1=[0, 1], x2=2, x4="8"))
        self.assertEqual(repr(d), "D(x=1, c=_CorgyCls(x1=[0, 1], x2=2, x3=3, x4='8'))")

    def test_corgy_cls_as_dict(self):
        c = self._CorgyCls(x1=[0, 1], x2=2, x3=30, x4="40")
        self.assertDictEqual(c.as_dict(), {"x1": [0, 1], "x2": 2, "x3": 30, "x4": "40"})

    def test_corgy_cls_as_dict_uses_default_values(self):
        c = self._CorgyCls(x1=[0, 1], x2=2, x3=30)
        self.assertDictEqual(c.as_dict(), {"x1": [0, 1], "x2": 2, "x3": 30, "x4": "4"})

    def test_corgy_cls_as_dict_ignores_unset_attrs_without_defaults(self):
        c = self._CorgyCls(x3=30, x4="40")
        self.assertDictEqual(c.as_dict(), {"x3": 30, "x4": "40"})

    def test_corgy_cls_as_dict_handles_groups(self):
        class D(Corgy):
            x: int
            c: self._CorgyCls

        c = self._CorgyCls()
        d = D(x=1, c=c)
        self.assertDictEqual(d.as_dict(), {"x": 1, "c": c})


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

    def test_add_args_handles_custom_metavar(self):
        class T:
            __metavar__ = "T"

        class C(Corgy):
            x: T

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=T, required=True, metavar="T"
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

    @skipIf(sys.version_info < (3, 10), "`|` syntax needs Python 3.10 or higher")
    def test_add_args_handles_annotated_new_style_optional(self):
        class C(Corgy):
            x: int | None  # type: ignore # pylint: disable=unsupported-binary-operation

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

    def test_add_args_handles_custom_flag(self):
        class C(Corgy):
            the_x_arg: Annotated[int, "x help", ["-x", "--the-x", "--the-x-arg"]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "-x",
            "--the-x",
            "--the-x-arg",
            type=int,
            required=True,
            help="x help",
            dest="the_x_arg",
        )

    def test_add_args_uses_positional_flag(self):
        class C(Corgy):
            the_x_arg: Annotated[int, "x help", ["x"]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "the_x_arg", type=int, help="x help"
        )

    def test_add_handles_positional_flag_with_same_name(self):
        class C(Corgy):
            the_x_arg: Annotated[int, "x help", ["the-x-arg"]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "the_x_arg", type=int, help="x help"
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

    def test_add_args_uses_base_class_for_choice_type(self):
        class A:
            ...

        class A1(A):
            ...

        class A2(A):
            ...

        class B:
            ...

        class B1(B):
            ...

        class BA1(B, A2):
            ...

        class C(Corgy):
            x: Literal[A1, A2, BA1]  # type: ignore

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=A, required=True, choices=(A1, A2, BA1)
        )

        with self.assertRaises(TypeError):

            class D(Corgy):
                x: Literal[A1, A2, B1]  # type: ignore

            D.add_args_to_parser(self.parser)

    def test_add_args_uses_custom_choices(self):
        class A:
            __choices__ = (1, 2, 3)

        class C(Corgy):
            x: A

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=A, required=True, choices=(1, 2, 3)
        )

    def test_add_args_handles_user_defined_class_as_type(self):
        class T:
            ...

        class C(Corgy):
            x: T

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=T, required=True)

    def test_add_args_handles_user_defined_object_as_default(self):
        class T:
            ...

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
            "--x", type=bool, action=BooleanOptionalAction, required=True
        )

    def test_add_args_handles_default_for_bool_type(self):
        class C(Corgy):
            x: bool = False

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, action=BooleanOptionalAction, default=False
        )

    def test_add_args_does_not_convert_bool_sequence_to_action(self):
        class C(Corgy):
            x: Sequence[bool]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, required=True, nargs="*"
        )

    def test_add_args_raises_if_sequence_has_no_types(self):
        class C(Corgy):
            x: Sequence

        class D(Corgy):
            x: SequenceType

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

        with self.assertRaises(TypeError):
            D.add_args_to_parser(self.parser)

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

    @skipIf(sys.version_info < (3, 9), "`typing.Sequence` doesn't accept multiple args")
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

    @skipIf(sys.version_info < (3, 9), "`typing.Sequence` doesn't accept multiple args")
    def test_add_args_handles_fixed_length_sequence_with_chocies(self):
        class C(Corgy):
            x: Sequence[Literal[1, 2, 3], Literal[1, 2, 3]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs=2, required=True, choices=(1, 2, 3)
        )

    @skipIf(sys.version_info < (3, 9), "`typing.Sequence` doesn't accept multiple args")
    def test_add_args_raises_if_fixed_length_sequence_choices_not_all_same(self):
        class C(Corgy):
            x: Sequence[Literal[1, 2, 3], Literal[1, 2]]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    @skipIf(sys.version_info < (3, 9), "`typing.Sequence` doesn't accept multiple args")
    def test_add_args_handles_fixed_length_typed_sequence(self):
        class C(Corgy):
            x: Sequence[int, int, int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs=3, required=True
        )

    @skipIf(sys.version_info < (3, 9), "`typing.Sequence` doesn't accept multiple args")
    def test_add_args_handles_length_2_typed_sequence(self):
        class C(Corgy):
            x: Sequence[int, int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, nargs=2, required=True
        )

    @skipIf(sys.version_info < (3, 9), "`typing.Sequence` doesn't accept multiple args")
    def test_add_args_raises_if_fixed_length_sequence_types_not_all_same(self):
        class C(Corgy):
            x: Sequence[int, str, int]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    def test_add_args_converts_corgy_var_to_argument_group(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            g: Annotated[G, "group G"]

        grp_parser = MagicMock()
        self.parser.add_argument_group = MagicMock(return_value=grp_parser)

        C.add_args_to_parser(self.parser)
        self.parser.add_argument_group.assert_called_once_with("g", "group G")
        grp_parser.add_argument.assert_called_once_with(
            "--g:x", type=int, required=True
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

    def test_add_args_handles_custom_flags_inside_group(self):
        class G(Corgy):
            the_x_arg: Annotated[int, "x help", ["-x", "--the-x", "--the-x-arg"]]

        class C(Corgy):
            the_grp: G

        grp_parser = MagicMock()
        self.parser.add_argument_group.return_value = grp_parser

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_not_called()
        self.parser.add_argument_group.assert_called_once_with("the_grp", None)
        grp_parser.add_argument.assert_called_once_with(
            "--the-grp:x",
            "--the-grp:the-x",
            "--the-grp:the-x-arg",
            type=int,
            help="x help",
            required=True,
            dest="the_grp:the_x_arg",
        )

    def test_add_args_handles_custom_flags_of_positional_args_inside_group(self):
        class G(Corgy):
            the_x_arg: Annotated[int, "x help", ["x", "the-x", "the_x_arg"]]

        grp_parser = argparse.ArgumentParser()
        grp_parser.add_argument = MagicMock()
        G.add_args_to_parser(grp_parser)
        grp_parser.add_argument.assert_called_once_with(
            "the_x_arg", type=int, help="x help"
        )

        class C(Corgy):
            the_grp: G

        grp_parser = MagicMock()
        self.parser.add_argument_group.return_value = grp_parser

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_not_called()
        self.parser.add_argument_group.assert_called_once_with("the_grp", None)
        grp_parser.add_argument.assert_called_once_with(
            "--the-grp:x",
            "--the-grp:the-x",
            "--the-grp:the_x_arg",
            type=int,
            help="x help",
            required=True,
            dest="the_grp:the_x_arg",
        )

    def test_add_args_makes_nested_groups_flat(self):
        class G2(Corgy):
            x: int

        class G1(Corgy):
            x: int
            g2: G2

        class C(Corgy):
            x: int
            g1: G1

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, required=True)
        self.parser.add_argument_group.assert_any_call("g1", None)
        self.parser.add_argument_group.assert_any_call("g1:g2", None)

    def test_add_args_infers_correct_base_type_from_complex_type_hint(self):
        class C(Corgy):
            x: Annotated[Optional[Sequence[str]], "x"]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=str, help="x", nargs="*"
        )

    def test_add_args_allows_function_base_type(self):
        def f(x: str) -> int:
            return int(x)

        class C(Corgy):
            x: f

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=f, required=True)

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

    def test_cmdline_args_are_parsed_with_custom_flags(self):
        class C(Corgy):
            var: Annotated[int, "x help", ["-x", "--the-x", "--the-x-arg"]]

        for flag in ["-x", "--the-x", "--the-x-arg"]:
            with self.subTest(flag=flag):
                self.parser = argparse.ArgumentParser()
                self.parser.parse_args = lambda: self.orig_parse_args(
                    self.parser, ["-x", "1"]
                )
                c = C.parse_from_cmdline(self.parser)
                self.assertEqual(c.var, 1)

    def test_cmdline_positional_args_are_parsed_with_custom_flags(self):
        class C(Corgy):
            var: Annotated[int, "x help", ["x"]]

        self.parser = argparse.ArgumentParser()
        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["1"])
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.var, 1)

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

    def test_cmdline_parsing_handles_groups_with_positional_args(self):
        class G(Corgy):
            the_x_var: Annotated[int, "x help", ["x", "the_x", "the-x-var"]]

        grp_parser = argparse.ArgumentParser()
        grp_parser.parse_args = lambda: self.orig_parse_args(grp_parser, ["1"])
        g = G.parse_from_cmdline(grp_parser)
        self.assertEqual(g.the_x_var, 1)

        class C(Corgy):
            x: int
            g: G

        for grp_flag in ["--g:x", "--g:the-x", "--g:the-x-var"]:
            with self.subTest(grp_flag=grp_flag):
                self.setUp()
                self.parser.parse_args = lambda: self.orig_parse_args(
                    self.parser,
                    ["--x", "1", grp_flag, "2"],  # pylint: disable=cell-var-from-loop
                )
                c = C.parse_from_cmdline(self.parser)
                self.assertEqual(c.x, 1)
                self.assertEqual(c.g.the_x_var, 2)

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

    def test_cmdline_parsing_handles_nested_groups_with_custom_flags(self):
        class G1(Corgy):
            var: Annotated[int, "var help", ["-v", "--var"]]

        class G2(Corgy):
            var: Annotated[int, "var help", ["-v", "--var"]]
            g: G1

        class C(Corgy):
            var: Annotated[int, "var help", ["-v", "--var"]]
            g1: G1
            g2: G2

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["-v", "1", "--g1:v", "2", "--g2:var", "3", "--g2:g:v", "4"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.var, 1)
        self.assertEqual(c.g1.var, 2)
        self.assertEqual(c.g2.var, 3)
        self.assertEqual(c.g2.g.var, 4)

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
            "corgy._corgy.argparse.ArgumentParser", MagicMock(return_value=self.parser)
        ):
            C.parse_from_cmdline(
                formatter_class=argparse.ArgumentDefaultsHelpFormatter, add_help=False
            )
            corgy._corgy.argparse.ArgumentParser.assert_called_once_with(
                formatter_class=argparse.ArgumentDefaultsHelpFormatter, add_help=False
            )

    def test_parse_from_cmdline_uses_corgy_help_formatter_if_no_formatter_specified(
        self,
    ):
        class C(Corgy):
            x: int

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["--x", "1"])
        with patch(
            "corgy._corgy.argparse.ArgumentParser", MagicMock(return_value=self.parser)
        ):
            C.parse_from_cmdline(add_help=False)
            corgy._corgy.argparse.ArgumentParser.assert_called_once_with(
                formatter_class=CorgyHelpFormatter, add_help=False
            )

    def test_parse_from_cmdline_ignores_extra_arguments(self):
        class C(Corgy):
            x: int

        self.parser.add_argument("--y", type=str)
        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "1", "--y", "2"]
        )
        c = C.parse_from_cmdline(self.parser, add_help=False)
        self.assertEqual(c.x, 1)
        with self.assertRaises(AttributeError):
            _ = c.y


class TestCorgyCustomParsers(unittest.TestCase):
    """Tests to check usage of the @corgyparser decorator."""

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
                def parsex(s: str):  # type: ignore # pylint: disable=no-self-argument
                    return 0

    def test_add_args_handles_corgyparser(self):
        class C(Corgy):
            x: Annotated[int, "x"]

            @corgyparser("x")
            def parsex(s: str):  # type: ignore # pylint: disable=no-self-argument
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
            def parsex(s: str):  # type: ignore # pylint: disable=no-self-argument
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
            def parsex(s: str):  # type: ignore # pylint: disable=no-self-argument
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
            def parsex(s: str):  # type: ignore # pylint: disable=no-self-argument
                return -1

        parser = argparse.ArgumentParser()
        orig_parse_args = argparse.ArgumentParser.parse_args
        parser.parse_args = lambda: orig_parse_args(parser, ["--x", "test"])

        args = C.parse_from_cmdline(parser)
        self.assertEqual(args.x, -1)

    def test_corgyparser_allows_decorating_staticmethod(self):
        class C(Corgy):
            x: int

            @corgyparser("x")
            @staticmethod
            def parsex(s: str):
                return 0

        parser = argparse.ArgumentParser()
        orig_parse_args = argparse.ArgumentParser.parse_args
        parser.parse_args = lambda: orig_parse_args(parser, ["--x", "test"])

        c = C.parse_from_cmdline(parser)
        self.assertEqual(c.x, 0)

    def test_corgyparser_raises_if_decorating_non_staticmethod(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int

                @corgyparser("x")
                @classmethod
                def parsex(cls, s: str):
                    return 0

    def test_corgyparser_functions_are_callable(self):
        class C(Corgy):
            x: int
            y: int

            @corgyparser("x")
            @staticmethod
            def parsex(s: str):
                return 0

            @corgyparser("y")
            def parsey(s: str):  # type: ignore # pylint: disable=no-self-argument
                return 1

        self.assertEqual(C.parsex("x"), 0)
        self.assertEqual(C.parsey("y"), 1)

    def test_corgyparser_decorators_can_be_chained(self):
        class C(Corgy):
            x: int
            y: int

            @corgyparser("x")
            @corgyparser("y")
            @staticmethod
            def parsexy(s: str):
                return int(s)

        self.assertEqual(C.parsexy("1"), 1)
        self.assertEqual(C.parsexy("2"), 2)

    def test_add_args_with_custom_parser_uses_custom_metavar(self):
        class T:
            __metavar__ = "T"

        class C(Corgy):
            x: T

            @corgyparser("x")
            @staticmethod
            def parsex(s: str):
                return 0

        parser = argparse.ArgumentParser()
        parser.add_argument = MagicMock()
        C.add_args_to_parser(parser)
        parser.add_argument.assert_called_once_with(
            "--x", type=C.parsex.fparse, required=True, metavar="T"
        )
