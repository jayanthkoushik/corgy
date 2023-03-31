import os
from pathlib import Path
from stat import S_IEXEC, S_IREAD, S_IWRITE
from tempfile import TemporaryDirectory
from typing import Type, Union
from unittest import skipIf, TestCase
from unittest.mock import MagicMock, patch

from corgy.types import (
    InputDirectory,
    IODirectory,
    LazyOutputDirectory,
    OutputDirectory,
)

from ._specialtmps import temp_dir_in_home, temp_env_var_dir


class _TestDirectoryWrapper:
    class TestDirectory(TestCase):
        type: Union[Type[OutputDirectory], Type[InputDirectory], Type[IODirectory]]

        def setUp(self):
            self.tmp_dir = TemporaryDirectory()  # pylint: disable=consider-using-with

        def tearDown(self):
            self.tmp_dir.cleanup()

        def test_directory_returns_pathlib_path(self):
            d = self.type(self.tmp_dir.name)
            self.assertIsInstance(d, self.type)
            self.assertIsInstance(d, Path)
            self.assertEqual(str(d), self.tmp_dir.name)

        def test_directory_raises_if_path_not_dir(self):
            fname = os.path.join(self.tmp_dir.name, "foo.file")
            open(  # pylint: disable=unspecified-encoding,consider-using-with
                fname, "x"
            ).close()
            with self.assertRaises(ValueError):
                self.type(fname)

        def test_directory_repr(self):
            d = self.type(self.tmp_dir.name)
            self.assertEqual(repr(d), f"{self.type.__name__}({self.tmp_dir.name!r})")
            self.assertEqual(str(d), self.tmp_dir.name)

        def test_directory_accepts_path(self):
            d = self.type(Path(self.tmp_dir.name))
            self.assertEqual(str(d), self.tmp_dir.name)

        def test_directory_expands_user(self):
            with temp_dir_in_home(self) as d:
                td = self.type(os.path.join("~", d.name))
                self.assertEqual(str(td), str(d))

        def test_directory_does_not_expand_user_if_disabled(self):
            class D(self.type):
                do_expanduser = False

            with temp_dir_in_home(self) as d:
                if issubclass(self.type, OutputDirectory):
                    td = D(os.path.join("~", d.name))
                    td.init()
                    self.assertNotEqual(str(td), str(d))
                    os.rmdir(td)
                    os.rmdir("~")
                else:
                    with self.assertRaises(ValueError):
                        D(os.path.join("~", d.name))

        def test_directory_expands_env_var(self):
            with temp_env_var_dir(self) as (env_var, d):
                td = self.type(f"${env_var}")
                self.assertEqual(str(td), str(d))

        def test_directory_does_not_expand_env_var_if_disabled(self):
            class D(self.type):
                do_expandvars = False

            with temp_env_var_dir(self) as (env_var, d):
                if issubclass(self.type, OutputDirectory):
                    td = D(f"${env_var}")
                    td.init()
                    self.assertNotEqual(str(td), str(d))
                    os.rmdir(td)
                else:
                    with self.assertRaises(ValueError):
                        D(f"${env_var}")


class TestOutputDirectory(_TestDirectoryWrapper.TestDirectory):
    type = OutputDirectory

    def test_output_directory_creates_dir_if_not_exists(self):
        dname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz")
        self.type(dname)
        self.assertTrue(os.path.exists(dname))

    def test_output_directory_raises_if_dir_create_fails(self):
        with patch("corgy.types._dir.os.makedirs", MagicMock(side_effect=OSError)):
            with self.assertRaises(ValueError):
                self.type(os.path.join(self.tmp_dir.name, "foo", "bar", "baz"))

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_output_directory_raises_if_dir_not_writeable(self):
        dname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz")
        os.makedirs(dname)
        os.chmod(dname, S_IREAD | S_IEXEC)
        with self.assertRaises(ValueError):
            self.type(dname)
        os.chmod(dname, S_IREAD | S_IWRITE | S_IEXEC)


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


class TestInputDirectory(_TestDirectoryWrapper.TestDirectory):
    type = InputDirectory

    def test_input_directory_raises_if_dir_not_exists(self):
        with self.assertRaises(ValueError):
            self.type(os.path.join(self.tmp_dir.name, "nota.dir"))

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_input_directory_raises_if_dir_not_readable(self):
        dname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz")
        os.makedirs(dname)
        os.chmod(dname, 0)
        with self.assertRaises(ValueError):
            self.type(dname)
        os.chmod(dname, S_IREAD | S_IWRITE | S_IEXEC)


class TestIODirectory(_TestDirectoryWrapper.TestDirectory):
    type = IODirectory

    test_io_directory_raises_if_dir_not_exists = (
        TestInputDirectory.test_input_directory_raises_if_dir_not_exists
    )
    test_io_directory_raises_if_dir_not_readable = (
        TestInputDirectory.test_input_directory_raises_if_dir_not_readable
    )
    test_io_directory_raises_if_dir_not_writeable = (
        TestOutputDirectory.test_output_directory_raises_if_dir_not_writeable
    )
