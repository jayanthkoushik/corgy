import os
from pathlib import Path
from stat import S_IEXEC, S_IREAD, S_IWRITE
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest import skipIf, TestCase

from corgy.types import ReadableFile, WritableFile

from ._specialtmps import temp_env_var_file, temp_file_in_home


class TestReadableFile(TestCase):
    def test_readable_file_is_path(self):
        with NamedTemporaryFile() as f:
            p = ReadableFile(f.name)
            self.assertIsInstance(p, ReadableFile)
            self.assertIsInstance(p, Path)
            self.assertEqual(p, Path(f.name))

    def test_readable_file_raises_if_file_not_exists(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                ReadableFile(os.path.join(d, "foo.file"))

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_readable_file_raises_if_file_not_readable(self):
        with NamedTemporaryFile() as f:
            os.chmod(f.name, S_IWRITE)
            with self.assertRaises(ValueError):
                ReadableFile(f.name)
            os.chmod(f.name, S_IREAD | S_IWRITE)

    def test_readable_file_raises_if_path_not_file(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                ReadableFile(d)

    def test_readable_file_expands_user(self):
        with temp_file_in_home(self) as fpath:
            p = ReadableFile(os.path.join("~", fpath.relative_to(Path.home())))
            self.assertEqual(p, fpath)

    def test_readable_file_does_not_expand_user_if_disabled(self):
        class RF(ReadableFile):
            do_expanduser = False

        with temp_file_in_home(self) as fpath:
            with self.assertRaises(ValueError):
                RF(os.path.join("~", fpath.name))

    def test_readable_file_expands_env_var(self):
        with temp_env_var_file(self) as (env_var, fpath):
            p = ReadableFile(f"${env_var}")
            self.assertEqual(p, fpath)

    def test_readable_file_does_not_expand_env_var_if_disabled(self):
        class RF(ReadableFile):
            do_expandvars = False

        with temp_env_var_file(self) as (env_var, _):
            with self.assertRaises(ValueError):
                RF(f"${env_var}")


class TestWritableFile(TestCase):
    def test_writable_file_is_path(self):
        with NamedTemporaryFile() as f:
            p = WritableFile(f.name)
            self.assertIsInstance(p, WritableFile)
            self.assertIsInstance(p, Path)
            self.assertEqual(p, Path(f.name))

    def test_writable_file_works_when_file_not_exists(self):
        with TemporaryDirectory() as d:
            WritableFile(os.path.join(d, "foo.file"))

    def test_writable_file_raises_if_path_not_file(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                WritableFile(d)

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_writable_file_raises_if_file_not_writeable(self):
        with NamedTemporaryFile() as f:
            os.chmod(f.name, S_IREAD)
            with self.assertRaises(ValueError):
                WritableFile(f.name)
            os.chmod(f.name, S_IREAD | S_IWRITE)

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_writable_file_raises_if_file_not_exists_and_dir_not_writeable(self):
        with TemporaryDirectory() as d:
            os.chmod(d, S_IREAD | S_IEXEC)
            with self.assertRaises(ValueError):
                WritableFile(os.path.join(d, "foo.file"))
            os.chmod(d, S_IREAD | S_IWRITE | S_IEXEC)

    @skipIf(os.name == "nt", "`chmod` does not seem to work on Windows")
    def test_writable_file_works_if_file_exists_and_dir_not_writeable(self):
        with TemporaryDirectory() as d:
            with open(os.path.join(d, "foo.file"), "xb"):
                pass
            os.chmod(d, S_IREAD | S_IEXEC)
            with self.assertRaises(ValueError):
                WritableFile(os.path.join(d, "bar.file"))
            WritableFile(os.path.join(d, "foo.file"))
            os.chmod(d, S_IREAD | S_IWRITE | S_IEXEC)

    def test_writable_file_handles_current_dir(self):
        with NamedTemporaryFile(dir=".") as f:
            fpath = Path(f.name)
            self.assertEqual(WritableFile(fpath.name).absolute(), fpath.absolute())

    def test_writable_file_expands_user(self):
        with temp_file_in_home(self) as fpath:
            p = WritableFile(os.path.join("~", fpath.relative_to(Path.home())))
            self.assertEqual(p, fpath)

    def test_writable_file_does_not_expand_user_if_disabled(self):
        class WF(WritableFile):
            do_expanduser = False

        with temp_file_in_home(self) as fpath:
            with self.assertRaises(ValueError):
                WF(os.path.join("~", fpath.name))

    def test_writable_file_expands_env_var(self):
        with temp_env_var_file(self) as (env_var, fpath):
            p = WritableFile(f"${env_var}")
            self.assertEqual(p, fpath)

    def test_writable_file_does_not_expand_env_var_if_disabled(self):
        class WF(WritableFile):
            do_expandvars = False

        with temp_env_var_file(self) as (env_var, fpath):
            p = WF(f"${env_var}")
            self.assertNotEqual(p, fpath)
