import pickle
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipIf, TestCase

from corgy import Corgy
from corgy.types import InitArgs

from ._pklclasses import PklTestA


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

    def test_init_args_pickleable(self):
        with TemporaryDirectory() as _tmpdir:
            _pkl_path = Path(_tmpdir) / "tmp.pkl"

            _IAT = InitArgs[PklTestA]
            _iat = _IAT(x=1)

            with _pkl_path.open("wb") as _f:
                pickle.dump(_iat, _f)

            with _pkl_path.open("rb") as _f:
                _iat = pickle.load(_f)

            self.assertEqual(_iat, _IAT(x=1))
