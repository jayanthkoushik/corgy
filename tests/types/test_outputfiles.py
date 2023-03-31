import os
import sys
from io import BufferedWriter, TextIOWrapper
from pathlib import Path
from stat import S_IREAD, S_IWRITE
from tempfile import TemporaryDirectory
from typing import Type, Union
from unittest import skipIf
from unittest.mock import MagicMock, patch

from corgy.types import (
    LazyOutputBinFile,
    LazyOutputTextFile,
    OutputBinFile,
    OutputTextFile,
)

from ._test_file import TestFileWrapper


class _TestOutputFileWrapper:
    class TestOutputFile(TestFileWrapper.TestFile):
        def test_output_file_creates_dir_if_not_exists(self):
            fname = os.path.join(self.tmp_dir.name, "foo", "bar", "baz.file")
            with self.type(fname):
                self.assertTrue(os.path.exists(fname))

        def test_output_file_raises_if_dir_create_fails(self):
            with patch("corgy.types._dir.os.makedirs", MagicMock(side_effect=OSError)):
                with self.assertRaises(ValueError):
                    self.type(os.path.join(self.tmp_dir.name, "foo", "bar", "baz.file"))

        @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
        def test_output_file_fails_if_file_not_writeable(self):
            fname = os.path.join(self.tmp_dir.name, "foo.file")
            open(  # pylint: disable=unspecified-encoding,consider-using-with
                fname, "x"
            ).close()
            os.chmod(fname, S_IREAD)
            with self.assertRaises(ValueError):
                self.type(fname)
            os.chmod(fname, S_IREAD | S_IWRITE)

        def test_output_file_handles_existing_file(self):
            fname = os.path.join(self.tmp_dir.name, "foo.file")
            with open(fname, "wb") as f:
                f.write(b"foo")
            of = self.type(fname)
            with open(fname, "rb") as f:
                self.assertEqual(f.read(), b"")
            of.close()

        def test_output_file_repr_str(self):
            fname = os.path.join(self.tmp_dir.name, "foo.file")
            with self.type(fname) as f:
                self.assertEqual(repr(f), f"{self.type.__name__}({fname!r})")
                self.assertEqual(str(f), fname)

        def test_output_file_accepts_path(self):
            fname = self.tmp_dir.name / Path("foo.file")
            with self.type(fname):
                self.assertTrue(fname.exists())


class TestOutputTextFile(_TestOutputFileWrapper.TestOutputFile):
    type = OutputTextFile

    def test_output_text_file_type(self):
        with self.type(os.path.join(self.tmp_dir.name, "foo.txt")) as f:
            self.assertIsInstance(f, TextIOWrapper)

    def test_output_text_file_stdouterr_wrappers(self):
        for wrapper, buffer in zip(
            [OutputTextFile.stdout_wrapper(), OutputTextFile.stderr_wrapper()],
            [sys.__stdout__.buffer, sys.__stderr__.buffer],
        ):
            with self.subTest(wrapper=wrapper):
                self.assertIsInstance(wrapper, OutputTextFile)
                self.assertIs(wrapper.buffer, buffer)


class TestOutputBinFile(_TestOutputFileWrapper.TestOutputFile):
    type = OutputBinFile

    def test_output_bin_file_type(self):
        with self.type(os.path.join(self.tmp_dir.name, "foo.bin")) as f:
            self.assertIsInstance(f, BufferedWriter)

    def test_output_bin_file_stdouterr_wrappers(self):
        for wrapper, buffer in zip(
            [OutputBinFile.stdout_wrapper(), OutputBinFile.stderr_wrapper()],
            [sys.__stdout__.buffer, sys.__stderr__.buffer],
        ):
            with self.subTest(wrapper=wrapper):
                self.assertIsInstance(wrapper, OutputBinFile)
                self.assertEqual(wrapper.fileno(), buffer.fileno())


class _TestLazyOutputFileWrapper:
    class TestLazyOutputFile(TestFileWrapper.TestFile):
        type: Union[Type[LazyOutputTextFile], Type[LazyOutputBinFile]]

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

        def test_lazy_output_file_handles_existing_file(self):
            with TemporaryDirectory() as tmp_dir:
                fpath = os.path.join(tmp_dir, "foo.file")
                with open(fpath, "wb") as f:
                    f.write(b"foo")
                lazyf = self.type(fpath)
                with open(fpath, "rb") as f:
                    self.assertEqual(f.read(), b"foo")
                lazyf.init()
                with open(fpath, "rb") as f:
                    self.assertEqual(f.read(), b"")
                lazyf.close()


class TestLazyOutputTextFile(_TestLazyOutputFileWrapper.TestLazyOutputFile):
    type = LazyOutputTextFile


class TestLazyOutputBinFile(_TestLazyOutputFileWrapper.TestLazyOutputFile):
    type = LazyOutputBinFile
