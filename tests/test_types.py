import os
from argparse import ArgumentTypeError
from io import IOBase
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory, TemporaryFile
from unittest import TestCase
from unittest.mock import MagicMock, patch

from corgy.types import (
    InputDirectoryType,
    InputFileType,
    OutputDirectoryType,
    OutputFileType,
    SubClassType,
)


class TestOutputFileType(TestCase):
    def setUp(self) -> None:
        self.type = OutputFileType()

    def test_output_file_type_raises_if_mode_not_w(self):
        OutputFileType("w")
        OutputFileType("wb")
        with self.assertRaises(ValueError):
            OutputFileType("r")
        with self.assertRaises(ValueError):
            InputFileType("r+")

    def test_output_file_type_creates_dir_if_not_exists(self):
        with TemporaryDirectory() as tmp_dir:
            fname = os.path.join(tmp_dir, "foo", "bar", "baz.txt")
            self.type(fname)
            self.assertTrue(os.path.exists(fname))
            self.assertTrue(os.access(fname, os.W_OK))

    def test_output_file_type_raises_if_dir_create_fails(self):
        with patch("corgy.types.os.makedirs", MagicMock(side_effect=OSError)):
            with TemporaryDirectory() as tmp_dir:
                with self.assertRaises(ArgumentTypeError):
                    self.type(os.path.join(tmp_dir, "foo", "bar", "baz.txt"))

    def test_output_file_type_returns_file_object(self):
        with TemporaryDirectory() as tmp_dir:
            fname = os.path.join(tmp_dir, "foo.txt")
            out_file = self.type(fname)
            self.assertIsInstance(out_file, IOBase)
            self.assertEqual(out_file.name, fname)


class TestInputFileType(TestCase):
    def setUp(self) -> None:
        self.type = InputFileType()

    def test_input_file_type_raises_if_mode_not_r(self):
        InputFileType("r")
        InputFileType("rb")
        with self.assertRaises(ValueError):
            InputFileType("w")
        with self.assertRaises(ValueError):
            InputFileType("r+")

    def test_input_file_type_raises_if_file_not_exists(self):
        with TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ArgumentTypeError):
                self.type(os.path.join(tmp_dir, "foo.txt"))

    def test_input_file_type_returns_file_object(self):
        with TemporaryFile() as tmp_file:
            in_file = self.type(tmp_file.name)
            self.assertIsInstance(in_file, IOBase)
            self.assertEqual(in_file.name, tmp_file.name)


class TestOutputDirectoryType(TestCase):
    def setUp(self) -> None:
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
    def setUp(self) -> None:
        self.type = InputDirectoryType()

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
        self.assertSetEqual(set(type_.choices()), {"B", "C", "D", "F"})