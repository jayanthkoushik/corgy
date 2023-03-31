import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Type, Union
from unittest import TestCase

from corgy.types import InputBinFile, InputTextFile, OutputBinFile, OutputTextFile

from ._specialtmps import temp_env_var_file, temp_file_in_home


class TestFileWrapper:
    # The main class is defined inside to prevent `unittest` from discovering it.
    class TestFile(TestCase):
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

        def test_file_is_correct_type(self):
            with TemporaryDirectory() as d:
                fpath = os.path.join(d, "foo.file")
                with open(fpath, "wb"):
                    pass
                p = self.type(fpath)
                if issubclass(self.type, (OutputTextFile, OutputBinFile)):
                    p.init()
                self.assertIsInstance(p, self.type)
                p.close()

        def test_file_expands_user(self):
            with temp_file_in_home(self) as fpath:
                f = self.type(os.path.join("~", fpath.relative_to(Path.home())))
                if issubclass(self.type, (OutputTextFile, OutputBinFile)):
                    f.init()
                self.assertEqual(str(f), str(fpath))
                f.close()

        def test_file_does_not_expand_user_if_disabled(self):
            class F(self.type):
                do_expanduser = False

            with temp_file_in_home(self) as fpath:
                if issubclass(self.type, (InputTextFile, InputBinFile)):
                    with self.assertRaises(ValueError):
                        F(os.path.join("~", fpath.name))
                    return
                o = F(os.path.join("~", fpath.name))
                o.init()
                self.assertNotEqual(str(o), str(fpath))
                self.assertEqual(str(o), os.path.join("~", fpath.name))
                o.close()
                # Remove the file created by the test, and the '~' directory.
                os.remove(os.path.join(".", "~", fpath.name))
                os.rmdir(os.path.join(".", "~"))

        def test_file_expands_env_var(self):
            with temp_env_var_file(self) as (env_var, fpath):
                o = self.type(f"${env_var}")
                if issubclass(self.type, (OutputTextFile, OutputBinFile)):
                    o.init()
                self.assertEqual(str(o), str(fpath))
                o.close()

        def test_file_does_not_expand_env_var_if_disabled(self):
            class F(self.type):
                do_expandvars = False

            with temp_env_var_file(self) as (env_var, fpath):
                if issubclass(self.type, (InputTextFile, InputBinFile)):
                    with self.assertRaises(ValueError):
                        F(f"${env_var}")
                    return
                o = F(f"${env_var}")
                o.init()
                self.assertNotEqual(str(o), str(fpath))
                self.assertEqual(str(o), f"${env_var}")
                o.close()
                os.remove(os.path.join(".", f"${env_var}"))
