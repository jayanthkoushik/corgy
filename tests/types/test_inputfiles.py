import os
import sys
from io import BufferedReader, TextIOWrapper
from pathlib import Path
from stat import S_IREAD, S_IWRITE
from unittest import skipIf

from corgy.types import InputBinFile, InputTextFile

from ._test_file import TestFileWrapper


class _TestInputFileWrapper:
    class TestInputFile(TestFileWrapper.TestFile):
        def setUp(self):
            super().setUp()
            self.tmp_file_name = os.path.join(self.tmp_dir.name, "foo.file")
            open(  # pylint: disable=unspecified-encoding,consider-using-with
                self.tmp_file_name, "x"
            ).close()

        def test_input_file_raises_if_file_not_exists(self):
            with self.assertRaises(ValueError):
                self.type(os.path.join(self.tmp_dir.name, "nota.file"))

        @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
        def test_input_file_raises_if_file_not_readable(self):
            os.chmod(self.tmp_file_name, 0)
            with self.assertRaises(ValueError):
                self.type(self.tmp_file_name)
            os.chmod(self.tmp_file_name, S_IREAD | S_IWRITE)

        def test_input_file_repr_str(self):
            with self.type(self.tmp_file_name) as f:
                self.assertEqual(
                    repr(f), f"{self.type.__name__}({self.tmp_file_name!r})"
                )
                self.assertEqual(str(f), self.tmp_file_name)

        def test_input_file_accepts_path(self):
            fname = Path(self.tmp_file_name)
            with self.type(fname) as f:
                self.assertEqual(f.name, str(fname))


class TestInputTextFile(_TestInputFileWrapper.TestInputFile):
    type = InputTextFile

    def test_input_text_file_type(self):
        with self.type(self.tmp_file_name) as f:
            self.assertIsInstance(f, TextIOWrapper)

    def test_input_text_file_stdin_wrapper(self):
        wrapper = InputTextFile.stdin_wrapper()
        self.assertIsInstance(wrapper, InputTextFile)
        self.assertIs(wrapper.buffer, sys.__stdin__.buffer)


class TestInputBinFile(_TestInputFileWrapper.TestInputFile):
    type = InputBinFile

    def test_input_bin_file_type(self):
        with self.type(self.tmp_file_name) as f:
            self.assertIsInstance(f, BufferedReader)

    def test_input_bin_file_stdin_wrapper(self):
        wrapper = InputBinFile.stdin_wrapper()
        self.assertIsInstance(wrapper, InputBinFile)
        self.assertEqual(wrapper.fileno(), sys.__stdin__.buffer.fileno())
