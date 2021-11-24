import os
import sys
from argparse import ArgumentParser, ArgumentTypeError
from io import IOBase
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest import skipIf, TestCase
from unittest.mock import MagicMock, patch

from corgy.types import (
    InputDirectoryType,
    InputFileType,
    KeyValueType,
    OutputDirectoryType,
    OutputFileType,
    SubClassType,
)


class TestOutputFileType(TestCase):
    def setUp(self):
        self.type = OutputFileType()

    def test_output_file_type_accepts_write_modes(self):
        for mode in ["w", "a", "r+", "w+", "wt", "ba", "b+r", "+tw"]:
            with self.subTest(mode=mode):
                OutputFileType(mode)

    def test_output_file_type_raises_if_not_write_mode(self):
        for mode in ["r", "x"]:
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    OutputFileType(mode)

    def test_output_file_type_creates_dir_if_not_exists(self):
        with TemporaryDirectory() as tmp_dir:
            fname = os.path.join(tmp_dir, "foo", "bar", "baz.txt")
            self.type(fname).close()
            self.assertTrue(os.path.exists(fname))
            self.assertTrue(os.access(fname, os.W_OK))

    def test_output_file_type_raises_if_dir_create_fails(self):
        with patch("corgy.types.os.makedirs", MagicMock(side_effect=OSError)):
            with TemporaryDirectory() as tmp_dir:
                with self.assertRaises(ArgumentTypeError):
                    self.type(os.path.join(tmp_dir, "foo", "bar", "baz.txt")).close()

    def test_output_file_type_returns_file_object(self):
        with TemporaryDirectory() as tmp_dir:
            fname = os.path.join(tmp_dir, "foo.txt")
            with self.type(fname) as out_file:
                self.assertIsInstance(out_file, IOBase)
                self.assertEqual(out_file.name, fname)


class TestInputFileType(TestCase):
    def setUp(self):
        self.type = InputFileType()

    def test_input_file_type_accepts_read_modes(self):
        for mode in ["r", "rb", "tr"]:
            with self.subTest(mode=mode):
                InputFileType(mode)

    def test_input_file_type_raises_if_not_read_mode(self):
        for mode in ["w", "x", "a", "r+"]:
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    InputFileType(mode)

    def test_input_file_type_raises_if_file_not_exists(self):
        with TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ArgumentTypeError):
                self.type(os.path.join(tmp_dir, "foo.txt"))

    def test_input_file_type_returns_file_object(self):
        with TemporaryDirectory() as tmp_dir:
            fname = os.path.join(tmp_dir, "foo.txt")
            open(fname, "wb").close()  # pylint: disable=consider-using-with
            with self.type(fname) as in_file:
                self.assertIsInstance(in_file, IOBase)
                self.assertEqual(in_file.name, fname)


class TestOutputDirectoryType(TestCase):
    def setUp(self):
        self.type = OutputDirectoryType()

    def test_output_directory_type_creates_dir_if_not_exists(self):
        with TemporaryDirectory() as tmp_dir:
            dname = os.path.join(tmp_dir, "foo", "bar", "baz")
            self.type(dname)
            self.assertTrue(os.path.exists(dname))
            self.assertTrue(os.access(dname, os.W_OK))

    def test_output_directory_type_raises_if_path_not_dir(self):
        with NamedTemporaryFile() as tmp_file:
            with self.assertRaises(ArgumentTypeError):
                self.type(tmp_file.name)

    def test_output_directory_type_raises_if_dir_not_writable(self):
        def mock_os_access(_, mode):
            if mode == os.W_OK:
                return False
            return True

        with patch("corgy.types.os.access", MagicMock(side_effect=mock_os_access)):
            with TemporaryDirectory() as tmp_dir:
                with self.assertRaises(ArgumentTypeError):
                    self.type(tmp_dir)

    def test_output_directory_type_raises_if_dir_create_fails(self):
        with patch("corgy.types.os.makedirs", MagicMock(side_effect=OSError)):
            with TemporaryDirectory() as tmp_dir:
                with self.assertRaises(ArgumentTypeError):
                    self.type(os.path.join(tmp_dir, "foo"))

    def test_output_directory_type_returns_pathlib_path(self):
        with TemporaryDirectory() as tmp_dir:
            dname = os.path.join(tmp_dir, "foo", "bar", "baz")
            path = self.type(dname)
            self.assertIsInstance(path, Path)
            self.assertEqual(str(path), dname)


class TestInputDirectoryType(TestCase):
    def setUp(self):
        self.type = InputDirectoryType()

    def test_input_directory_type_raises_if_input_not_dir(self):
        with NamedTemporaryFile() as tmp_file:
            with self.assertRaises(ArgumentTypeError):
                self.type(tmp_file.name)

    def test_input_directory_type_raises_if_dir_not_exists(self):
        with TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ArgumentTypeError):
                self.type(os.path.join(tmp_dir, "foo"))

    def test_input_directory_type_raises_if_dir_not_readable(self):
        def mock_os_access(_, mode):
            if mode == os.R_OK:
                return False
            return True

        with patch("corgy.types.os.access", MagicMock(side_effect=mock_os_access)):
            with TemporaryDirectory() as tmp_dir:
                with self.assertRaises(ArgumentTypeError):
                    self.type(tmp_dir)

    def test_input_directory_type_returns_pathlib_path(self):
        with TemporaryDirectory() as tmp_dir:
            path = self.type(tmp_dir)
            self.assertIsInstance(path, Path)
            self.assertEqual(str(path), tmp_dir)


class TestSubClassType(TestCase):
    def test_subclass_type_returns_subclass(self):
        class A:
            ...

        class B(A):
            ...

        class C(A):
            ...

        type_ = SubClassType(A)
        self.assertIs(type_("B"), B)
        self.assertIs(type_("C"), C)

    def test_subclass_type_raises_if_not_subclass(self):
        class A:
            ...

        class B(A):  # pylint: disable=unused-variable
            ...

        type_ = SubClassType(A)
        with self.assertRaises(ArgumentTypeError):
            type_("C")

    def test_subclass_type_accepts_base_class_iff_allow_base_set(self):
        class A:
            ...

        type_ = SubClassType(A)
        with self.assertRaises(ArgumentTypeError):
            type_("A")

        type_ = SubClassType(A, allow_base=True)
        self.assertIs(type_("A"), A)

    def test_subclass_type_handles_nested_classes(self):
        class A:
            ...

        class B(A):
            ...

        class C(B):
            ...

        type_ = SubClassType(A)
        self.assertIs(type_("C"), C)

    def test_subclass_type_choices(self):
        class A:
            ...

        class B(A):
            ...

        class C(A):  # pylint: disable=unused-variable
            ...

        class D(B):  # pylint: disable=unused-variable
            ...

        class E:
            ...

        class F(A, E):  # pylint: disable=unused-variable
            ...

        type_ = SubClassType(A)
        self.assertSetEqual(set(type_.choices()), {B, C, D, F})

        type_ = SubClassType(A, allow_base=True)
        self.assertSetEqual(set(type_.choices()), {A, B, C, D, F})

    def test_subclass_type_with_argparse(self):
        class A:
            ...

        class B(A):
            ...

        class C(A):  # pylint: disable=unused-variable
            ...

        type_ = SubClassType(A)
        parser = ArgumentParser()
        parser.add_argument("--a", type=type_, choices=list(type_.choices()))
        args = parser.parse_args(["--a", "B"])
        self.assertIs(args.a, B)

    def test_subclass_type_with_full_names(self):
        class A:
            ...

        class B(A):
            ...

        class C(A):
            ...

        type_ = SubClassType(A, use_full_names=True)
        self.assertIs(type_(B.__module__ + "." + B.__qualname__), B)
        self.assertIs(type_(C.__module__ + "." + C.__qualname__), C)

    @skipIf(sys.version_info < (3, 9), "Python 3.9 or higher needed")
    def test_subclass_type_choices_with_corgy(self):
        class A:
            ...

        class B(A):
            ...

        class C(A):
            ...

        ASubClasses = SubClassType(A)

        from corgy import Corgy

        class D(Corgy):
            x: ASubClasses

        parser = ArgumentParser()
        parser.add_argument = MagicMock()
        D.add_args_to_parser(parser)
        parser.add_argument.assert_called_with(
            "--x", type=ASubClasses, choices=(B, C), required=True
        )


class TestKeyValuePairType(TestCase):
    def test_key_value_type_splits_input_string(self):
        type_ = KeyValueType()
        self.assertTupleEqual(type_("foo=bar"), ("foo", "bar"))

    def test_key_value_type_handles_type_casting(self):
        type_ = KeyValueType(int, float)
        self.assertTupleEqual(type_("1=2.0"), (1, 2.0))

    def test_key_value_type_default_metavar(self):
        type_ = KeyValueType()
        self.assertEqual(type_.__metavar__, "key=val")

    def test_key_value_type_handles_custom_separator(self):
        type_ = KeyValueType(separator=";")
        self.assertTupleEqual(type_("foo;bar"), ("foo", "bar"))
        self.assertEqual(type_.__metavar__, "key;val")

    def test_key_value_type_handles_multiple_separators(self):
        type_ = KeyValueType()
        self.assertTupleEqual(type_("foo=bar=baz"), ("foo", "bar=baz"))

    def test_key_value_type_raises_if_no_separator(self):
        type_ = KeyValueType()
        with self.assertRaises(ArgumentTypeError):
            type_("foo")

    def test_key_value_type_raises_if_bad_type(self):
        type_ = KeyValueType(int, int)
        with self.assertRaises(ArgumentTypeError):
            type_("foo=1")
        with self.assertRaises(ArgumentTypeError):
            type_("1=foo")

    def test_key_value_type_handles_function_as_type(self):
        type_ = KeyValueType(str, lambda x: x.upper())
        self.assertTupleEqual(type_("foo=bar"), ("foo", "BAR"))
