import os
import stat
import sys
from argparse import ArgumentTypeError
from io import BufferedReader, BufferedWriter, TextIOWrapper
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Type, Union
from unittest import skipIf, TestCase
from unittest.mock import MagicMock, patch

from corgy import Corgy
from corgy.types import (
    InitArgs,
    InputBinFile,
    InputDirectory,
    InputTextFile,
    KeyValuePairs,
    LazyOutputBinFile,
    LazyOutputDirectory,
    LazyOutputTextFile,
    OutputBinFile,
    OutputDirectory,
    OutputTextFile,
    SubClass,
)


class _TestFile(TestCase):
    type: Union[
        Type[OutputTextFile],
        Type[OutputBinFile],
        Type[InputTextFile],
        Type[InputBinFile],
    ]

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()  # pylint: disable=consider-using-with

    def tearDown(self):
        self.tmp_dir.cleanup()


class _TestOutputFile(_TestFile):
    def test_output_file_creates_dir_if_not_exists(self):
        fname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz.file")
        with self.type(fname):
            self.assertTrue(os.path.exists(fname))

    def test_output_file_raises_if_dir_create_fails(self):
        with patch("corgy.types.os.makedirs", MagicMock(side_effect=OSError)):
            with self.assertRaises(ArgumentTypeError):
                self.type(os.path.join(self.tmp_dir.name, "foo", "bar", "baz.file"))

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_output_file_fails_if_file_not_writeable(self):
        fname = os.path.join(self.tmp_dir.name, "foo.file")
        open(  # pylint: disable=unspecified-encoding,consider-using-with
            fname, "x"
        ).close()
        os.chmod(fname, stat.S_IREAD)
        with self.assertRaises(ArgumentTypeError):
            self.type(fname)
        os.chmod(fname, stat.S_IREAD | stat.S_IWRITE)

    def test_output_file_repr_str(self):
        fname = os.path.join(self.tmp_dir.name, "foo.file")
        with self.type(fname) as f:
            self.assertEqual(repr(f), f"{self.type.__name__}({fname!r})")
            self.assertEqual(str(f), fname)

    def test_output_file_accepts_path(self):
        fname = self.tmp_dir.name / Path("foo.file")
        with self.type(fname):
            self.assertTrue(fname.exists())


class TestOutputTextFile(_TestOutputFile):
    type = OutputTextFile

    def test_output_text_file_type(self):
        with self.type(os.path.join(self.tmp_dir.name, "foo.txt")) as f:
            self.assertIsInstance(f, TextIOWrapper)


class TestOutputBinFile(_TestOutputFile):
    type = OutputBinFile

    def test_output_bin_file_type(self):
        with self.type(os.path.join(self.tmp_dir.name, "foo.bin")) as f:
            self.assertIsInstance(f, BufferedWriter)


class _TestLazyOutputFile(_TestFile):
    type: Union[Type[LazyOutputTextFile], Type[LazyOutputBinFile],]

    def test_lazy_output_file_does_not_auto_create_file(self):
        fname = os.path.join(self.tmp_dir.name, "foo.file")
        self.type(fname)
        self.assertFalse(os.path.exists(fname))

    def test_lazy_output_file_creates_on_calling_init(self):
        fname = os.path.join(self.tmp_dir.name, "foo.file")
        f = self.type(fname)
        f.init()
        self.assertTrue(os.path.exists(fname))
        f.close()


class TestLazyOutputTextFile(_TestLazyOutputFile):
    type = LazyOutputTextFile


class TestLazyOutputBinFile(_TestLazyOutputFile):
    type = LazyOutputBinFile


class _TestInputFile(_TestFile):
    def setUp(self):
        super().setUp()
        self.tmp_file_name = os.path.join(self.tmp_dir.name, "foo.file")
        open(  # pylint: disable=unspecified-encoding,consider-using-with
            self.tmp_file_name, "x"
        ).close()

    def test_input_file_raises_if_file_not_exists(self):
        with self.assertRaises(ArgumentTypeError):
            self.type(os.path.join(self.tmp_dir.name, "nota.file"))

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_input_file_raises_if_file_not_readable(self):
        os.chmod(self.tmp_file_name, 0)
        with self.assertRaises(ArgumentTypeError):
            self.type(self.tmp_file_name)
        os.chmod(self.tmp_file_name, stat.S_IREAD | stat.S_IWRITE)

    def test_input_file_repr_str(self):
        with self.type(self.tmp_file_name) as f:
            self.assertEqual(repr(f), f"{self.type.__name__}({self.tmp_file_name!r})")
            self.assertEqual(str(f), self.tmp_file_name)

    def test_input_file_accepts_path(self):
        fname = Path(self.tmp_file_name)
        with self.type(fname) as f:
            self.assertEqual(f.name, str(fname))


class TestInputTextFile(_TestInputFile):
    type = InputTextFile

    def test_input_text_file_type(self):
        with self.type(self.tmp_file_name) as f:
            self.assertIsInstance(f, TextIOWrapper)


class TestInputBinFile(_TestInputFile):
    type = InputBinFile

    def test_input_bin_file_type(self):
        with self.type(self.tmp_file_name) as f:
            self.assertIsInstance(f, BufferedReader)


class _TestDirectory(TestCase):
    type: Union[Type[OutputDirectory], Type[InputDirectory]]

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()  # pylint: disable=consider-using-with

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_directory_returns_pathlib_path(self):
        d = self.type(self.tmp_dir.name)
        self.assertIsInstance(d, Path)
        self.assertEqual(str(d), self.tmp_dir.name)

    def test_directory_raises_if_path_not_dir(self):
        fname = os.path.join(self.tmp_dir.name, "foo.file")
        open(  # pylint: disable=unspecified-encoding,consider-using-with
            fname, "x"
        ).close()
        with self.assertRaises(ArgumentTypeError):
            self.type(fname)

    def test_directory_repr(self):
        with self.type(self.tmp_dir.name) as d:
            self.assertEqual(repr(d), f"{self.type.__name__}({self.tmp_dir.name!r})")
            self.assertEqual(str(d), self.tmp_dir.name)

    def test_directory_accepts_path(self):
        d = self.type(Path(self.tmp_dir.name))
        self.assertEqual(str(d), self.tmp_dir.name)


class TestOutputDirectory(_TestDirectory):
    type = OutputDirectory

    def test_output_directory_creates_dir_if_not_exists(self):
        dname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz")
        self.type(dname)
        self.assertTrue(os.path.exists(dname))

    def test_output_directory_raises_if_dir_create_fails(self):
        with patch("corgy.types.os.makedirs", MagicMock(side_effect=OSError)):
            with self.assertRaises(ArgumentTypeError):
                self.type(os.path.join(self.tmp_dir.name, "foo", "bar", "baz"))

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_output_directory_raises_if_dir_not_writeable(self):
        dname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz")
        os.makedirs(dname)
        os.chmod(dname, stat.S_IREAD | stat.S_IEXEC)
        with self.assertRaises(ArgumentTypeError):
            self.type(dname)
        os.chmod(dname, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)


class TestLazyOutputDirectory(TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()  # pylint: disable=consider-using-with

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_lazy_output_directory_does_not_auto_create_dir(self):
        dname = os.path.join(self.tmp_dir.name, "foo")
        LazyOutputDirectory(dname)
        self.assertFalse(os.path.exists(dname))

    def test_lazy_output_directory_creates_dir_on_init(self):
        dname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz")
        d = LazyOutputDirectory(dname)
        d.init()
        self.assertTrue(os.path.exists(dname))
        self.assertEqual(str(d), dname)


class TestInputDirectory(_TestDirectory):
    type = InputDirectory

    def test_input_directory_raises_if_dir_not_exists(self):
        with self.assertRaises(ArgumentTypeError):
            self.type(os.path.join(self.tmp_dir.name, "nota.dir"))

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_input_directory_raises_if_dir_not_readable(self):
        dname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz")
        os.makedirs(dname)
        os.chmod(dname, 0)
        with self.assertRaises(ArgumentTypeError):
            self.type(dname)
        os.chmod(dname, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)


class TestSubClass(TestCase):
    def test_subclass_raises_if_called_without_init(self):
        with self.assertRaises(TypeError):
            SubClass("X")

    def test_subclass_init_returns_unique_class(self):
        class A:
            ...

        type_ = SubClass[A]
        self.assertIsNot(type_, SubClass)

    def test_subclass_init_caches_calls(self):
        class A:
            ...

        type_ = SubClass[A]
        self.assertIs(type_, SubClass[A])

    def test_subclass_init_handles_type_being_unhashable(self):
        class M(type):
            __hash__ = None

        class A(metaclass=M):
            ...

        type_ = SubClass[A]
        self.assertIsNot(type_, SubClass[A])

    def test_subclass_raises_if_re_subscripted(self):
        class A:
            ...

        type_ = SubClass[A]
        with self.assertRaises(TypeError):
            type_[A]  # type: ignore # pylint: disable=pointless-statement

    def test_subclass_returns_arg_named_class(self):
        class A:
            ...

        class B(A):
            ...

        class C(A):
            ...

        type_ = SubClass[A]
        self.assertIsInstance(type_("B")(), B)
        self.assertIsInstance(type_("C")(), C)

    def test_subclass_raises_if_no_class_for_arg(self):
        class A:
            ...

        class _(A):
            ...

        type_ = SubClass[A]
        with self.assertRaises(ArgumentTypeError):
            type_("C")

    def test_subclass_raises_if_no_subclasses(self):
        class A:
            ...

        type_ = SubClass[A]
        with self.assertRaises(ArgumentTypeError):
            type_("A")

    def test_subclass_accepts_base_iff_allow_base_set(self):
        class A:
            ...

        type_ = SubClass[A]
        with self.assertRaises(ArgumentTypeError):
            type_("A")

        type_.allow_base = True
        self.assertIsInstance(type_("A")(), A)

    def test_subclass_accepts_nested_subs_unless_allow_indirect_subs_false(self):
        class A:
            ...

        class B(A):
            ...

        class C(B):
            ...

        type_ = SubClass[A]
        self.assertIsInstance(type_("C")(), C)

        type_.allow_indirect_subs = False
        with self.assertRaises(ArgumentTypeError):
            type_("C")

    def test_subclass_choices(self):
        class A:
            ...

        class B(A):  # pylint: disable=unused-variable
            ...

        class C(A):
            ...

        class D(C):  # pylint: disable=unused-variable
            ...

        type_ = SubClass[A]
        self.assertSetEqual(
            set(type_.__choices__), {type_("B"), type_("C"), type_("D")}
        )
        type_.allow_base = True
        self.assertSetEqual(
            set(type_.__choices__), {type_("A"), type_("B"), type_("C"), type_("D")}
        )

    def test_subclass_metavar(self):
        type_ = SubClass[int]
        self.assertEqual(type_.__metavar__, "cls")

    def test_subclass_call_with_params(self):
        class A:
            def __init__(self, x):
                ...

        class B(A):  # pylint: disable=unused-variable
            def __init__(self, x):  # pylint: disable=super-init-not-called
                self.x = f"B{x}"

        type_ = SubClass[A]
        b = type_("B")(1)
        self.assertEqual(b.x, "B1")

    def test_subclass_equality(self):
        class A:
            ...

        class B(A):  # pylint: disable=unused-variable
            ...

        class C(A):  # pylint: disable=unused-variable
            ...

        type_ = SubClass[A]
        type_.allow_base = True
        self.assertEqual(type_("B"), type_("B"))
        self.assertNotEqual(type_("B"), type_("C"))
        self.assertNotEqual(type_("A"), type_)

    def test_subclass_with_full_names(self):
        class A:
            ...

        class B(A):
            ...

        type_ = SubClass[A]
        type_.use_full_names = True
        with self.assertRaises(ArgumentTypeError):
            type_("B")
        self.assertIsInstance(type_(B.__module__ + "." + B.__qualname__)(), B)

    def test_subclass_caches_instances(self):
        class A:
            ...

        class B(A):  # pylint: disable=unused-variable
            ...

        class C(A):  # pylint: disable=unused-variable
            ...

        type_ = SubClass[A]
        self.assertIs(type_("B"), type_("B"))
        self.assertIs(type_("C"), type_("C"))

    def test_subclass_cache_handles_change_in_type_attributes(self):
        class A:
            ...

        class B(A):
            ...

        type_ = SubClass[A]
        init_b = type_("B")
        self.assertIs(type_("B"), init_b)

        type_.use_full_names = True
        with self.assertRaises(ArgumentTypeError):
            type_("B")

        new_b = type_(B.__module__ + "." + B.__qualname__)
        self.assertIsNot(new_b, init_b)
        self.assertIs(new_b, type_(B.__module__ + "." + B.__qualname__))

    def test_subclass_repr_str(self):
        class A:
            ...

        class B(A):  # pylint: disable=unused-variable
            ...

        type_ = SubClass[A]
        init_b = type_("B")

        self.assertEqual(repr(init_b), "SubClass[A]('B')")
        self.assertEqual(str(init_b), "B")

    def test_subclass_repr_str_with_full_names(self):
        class A:
            ...

        class B(A):
            ...

        type_ = SubClass[A]
        type_.use_full_names = True
        b_full_name = B.__module__ + "." + B.__qualname__
        init_b = type_(b_full_name)

        self.assertEqual(repr(init_b), f"SubClass[A]('{b_full_name}')")
        self.assertEqual(str(init_b), b_full_name)


class TestKeyValuePairs(TestCase):
    def test_key_value_pairs_init_returns_unique_class(self):
        type_ = KeyValuePairs[str, int]
        self.assertIsNot(type_, KeyValuePairs)

    def test_key_value_pairs_init_caches_calls(self):
        type_ = KeyValuePairs[str, int]
        self.assertIs(type_, KeyValuePairs[str, int])
        self.assertIsNot(type_, KeyValuePairs[int, str])

    def test_key_value_pairs_init_handles_type_being_unhashable(self):
        class M(type):
            __hash__ = None

        class A(metaclass=M):
            ...

        type_ = KeyValuePairs[A, str]
        self.assertIsNot(type_, KeyValuePairs[A, str])
        type_ = KeyValuePairs[str, A]
        self.assertIsNot(type_, KeyValuePairs[str, A])

    def test_key_value_pairs_raises_if_re_subscripted(self):
        type_ = KeyValuePairs[str, int]
        with self.assertRaises(TypeError):
            type_[str, int]  # type: ignore # pylint: disable=pointless-statement

    def test_key_value_pairs_returns_dict_like(self):
        type_ = KeyValuePairs[str, str]
        dic = type_("foo=1,bar=2")
        self.assertDictEqual(dic, {"foo": "1", "bar": "2"})

    def test_key_value_pairs_allows_call_without_init(self):
        dic = KeyValuePairs("foo=1,bar=2")
        self.assertDictEqual(dic, {"foo": "1", "bar": "2"})

    def test_key_value_pairs_handles_empty_string(self):
        self.assertDictEqual(KeyValuePairs(""), {})

    def test_key_value_pairs_raises_if_any_item_not_correct_format(self):
        with self.assertRaises(ArgumentTypeError):
            KeyValuePairs("foo=1,bar2")

    def test_key_value_pairs_handles_multiple_separators_in_item(self):
        dic = KeyValuePairs("foo==1,bar=2=3")
        self.assertDictEqual(dic, {"foo": "=1", "bar": "2=3"})

    def test_key_value_pairs_handles_type_casting(self):
        type_ = KeyValuePairs[int, float]
        dic = type_("1=2.0,3=4.0")
        self.assertDictEqual(dic, {1: float("2.0"), 3: float("4.0")})

    def test_key_value_pairs_raises_if_type_casting_fails(self):
        type_ = KeyValuePairs[int, int]
        with self.assertRaises(ArgumentTypeError):
            type_("foo=1")
        with self.assertRaises(ArgumentTypeError):
            type_("1=foo")

    def test_key_value_pairs_handles_type_casting_with_custom_type(self):
        class A:
            def __init__(self, x):
                self.x = x

            def __eq__(self, other):
                return isinstance(other, A) and self.x == other.x

        type_ = KeyValuePairs[str, A]
        dic = type_("foo=1,bar=2")
        self.assertDictEqual(dic, {"foo": A("1"), "bar": A("2")})

    def test_key_value_pairs_metavar(self):
        self.assertEqual(KeyValuePairs.__metavar__, "[key=val,...]")
        self.assertEqual(KeyValuePairs[str, int].__metavar__, "[key=val,...]")

    def test_key_value_pairs_handles_custom_sequence_separator(self):
        type_ = KeyValuePairs[str, str]
        with patch.object(type_, "sequence_separator", ";"):
            dic = type_("foo=1;bar=2")
            self.assertDictEqual(dic, {"foo": "1", "bar": "2"})
            self.assertEqual(type_.__metavar__, "[key=val;...]")

    def test_key_value_pairs_handles_custom_item_separator(self):
        type_ = KeyValuePairs[str, str]
        with patch.object(type_, "item_separator", ":"):
            dic = type_("foo:1,bar:2")
            self.assertDictEqual(dic, {"foo": "1", "bar": "2"})
            self.assertEqual(type_.__metavar__, "[key:val,...]")

    def test_key_value_pairs_subtype_not_affected_by_changes_to_base_type(self):
        type_ = KeyValuePairs[str, int]
        with patch.multiple(KeyValuePairs, sequence_separator=";", item_separator=":"):
            self.assertEqual(type_.sequence_separator, ",")
            self.assertEqual(type_.item_separator, "=")

    def test_key_value_pairs_repr_str(self):
        type_ = KeyValuePairs[str, int]
        dic = type_("foo=1,bar=2")
        self.assertEqual(repr(dic), "KeyValuePairs[str, int]('foo=1,bar=2')")
        self.assertEqual(str(dic), "{'foo': 1, 'bar': 2}")

    def test_key_value_pairs_repr_str_with_custom_separators(self):
        with patch.multiple(KeyValuePairs, sequence_separator=";", item_separator=":"):
            dic = KeyValuePairs("foo:1;bar:2")
            self.assertEqual(repr(dic), "KeyValuePairs[str, str]('foo:1;bar:2')")
            self.assertEqual(str(dic), "{'foo': '1', 'bar': '2'}")

    def test_key_value_pairs_accepts_dict(self):
        dic = KeyValuePairs[str, int]({"foo": 1, "bar": 2})
        self.assertDictEqual(dic, {"foo": 1, "bar": 2})
        self.assertEqual(repr(dic), "KeyValuePairs[str, int]({'foo': 1, 'bar': 2})")


class TestInitArgs(TestCase):
    def test_init_args_generates_correct_corgy_class(self):
        class A:
            def __init__(self, x: int, y: str):
                ...

        type_ = InitArgs[A]
        self.assertTrue(issubclass(type_, Corgy))
        self.assertTrue(hasattr(type_, "x"))
        self.assertIsInstance(type_.x, property)
        self.assertTrue(hasattr(type_, "y"))
        self.assertIsInstance(type_.y, property)

    def test_init_args_instance_can_be_used_to_init_class(self):
        class A:
            def __init__(self, x: int, y: str):
                self.x = x
                self.y = y

        type_ = InitArgs[A]
        a_args = type_(x=1, y="2")
        a = A(**a_args.as_dict())
        self.assertEqual(a.x, 1)
        self.assertEqual(a.y, "2")

    def test_init_args_raises_if_re_subscripted(self):
        class A:
            def __init__(self, x: int, y: str):
                ...

        type_ = InitArgs[A]
        with self.assertRaises(TypeError):
            type_ = type_[A]  # type: ignore

    def test_init_args_raises_if_missing_annotation(self):
        class A:
            def __init__(self, x: int, y):
                ...

        with self.assertRaises(TypeError):
            _ = InitArgs[A]

    def test_init_args_handles_default_values(self):
        class A:
            def __init__(self, x: int, y: str = "foo"):
                ...

        type_ = InitArgs[A]
        a_args = type_(x=1)
        self.assertDictEqual(a_args.as_dict(), {"x": 1, "y": "foo"})

    @skipIf(sys.version_info < (3, 8), "positional-only parameters require Python 3.8+")
    def test_init_args_raises_if_pos_only_arg_present(self):
        # We need to use `exec` to prevent syntax error in Python 3.7.
        # pylint: disable=exec-used
        exec(
            "class A:\n"
            "    def __init__(self, x: int, /, y: str): ...\n"
            "with self.assertRaises(TypeError):\n"
            "    InitArgs[A]",
            globals(),
            locals(),
        )


del _TestFile, _TestOutputFile, _TestLazyOutputFile, _TestInputFile, _TestDirectory
