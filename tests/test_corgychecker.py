import sys
from typing import ClassVar
from unittest import TestCase
from unittest.mock import MagicMock

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from corgy import Corgy, corgychecker


class TestCorgyCustomCheckers(TestCase):
    def test_corgychecker_raises_if_not_passed_name(self):
        with self.assertRaises(TypeError):

            @corgychecker
            def spam():
                ...

    def test_corgy_raises_if_corgychecker_target_invalid(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int

                @corgychecker("y")
                @staticmethod
                def check(s):
                    ...

    def test_corgy_raises_if_corgychecker_target_not_annotated(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int
                y = 1

                @corgychecker("y")
                @staticmethod
                def check(s):
                    ...

    def test_corgy_raises_if_corgychecker_target_classvar(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: ClassVar[int]

                @corgychecker("x")
                @staticmethod
                def check(s):
                    ...

    def test_corgychecker_allows_decorating_implicit_staticmethod(self):
        class C(Corgy):
            x: int

            @corgychecker("x")
            def check(s):  # type: ignore # pylint: disable=no-self-argument
                ...

        c = C()
        c.x = 1

    def test_corgychecker_raises_if_decorating_non_staticmethod(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int

                @corgychecker("x")
                @classmethod
                def check(cls, s):
                    ...

    def test_corgychecker_functions_are_callable(self):
        class C(Corgy):
            x: int
            y: int

            @corgychecker("x")
            @staticmethod
            def check_x(s):
                return 10

            @corgychecker("y")
            def check_y(s):  # type: ignore # pylint: disable=no-self-argument
                return 20

        self.assertEqual(C.check_x(1), 10)
        self.assertEqual(C.check_y(2), 20)

    def test_corgychecker_accepts_multiple_arguments(self):
        class C(Corgy):
            x: int
            y: int

            @corgychecker("x", "y")
            @staticmethod
            def check(s):
                ...

        self.assertIs(getattr(C, "__checkers")["x"], getattr(C, "__checkers")["y"])

    def test_corgychecker_decorators_can_be_chained(self):
        class C(Corgy):
            x: int
            y: int

            @corgychecker("x")
            @corgychecker("y")
            @staticmethod
            def check(s):
                ...

        self.assertIs(getattr(C, "__checkers")["x"], getattr(C, "__checkers")["y"])

    def test_corgychecker_is_called_on_setattr(self):
        mock_check = MagicMock()

        class C(Corgy):
            x: int
            y: int
            check = corgychecker("x")(mock_check)

        c = C()
        c.x = 1
        c.y = 2
        mock_check.assert_called_once_with(1)

    def test_corgychecker_is_called_after_setattr(self):
        mock_check = MagicMock()

        class C(Corgy):
            x: int
            check = corgychecker("x")(mock_check)

        c = C()
        with self.assertRaises(ValueError):
            c.x = "1"
        mock_check.assert_not_called()

    def test_setattr_raises_if_corgychecker_raises(self):
        class C(Corgy):
            x: int

            @corgychecker("x")
            @staticmethod
            def check(s):
                if s % 2:
                    raise ValueError

        c = C()
        c.x = 2
        with self.assertRaises(ValueError):
            c.x = 3

    def test_corgy_cls_inherits_custom_checker(self):
        class C(Corgy):
            x: int

            @corgychecker("x")
            @staticmethod
            def check(s):
                if s % 2:
                    raise ValueError

        class D(C):
            ...

        d = D()
        d.x = 2
        with self.assertRaises(ValueError):
            d.x = 1

    def test_corgychecker_works_with_self_type(self):
        class C(Corgy):
            x: int
            c: Self

            @corgychecker("c")
            @staticmethod
            def check(v: Self):
                if v.x % 2:
                    raise ValueError

        c = C()
        c.x = 1
        c.c = C(x=2)
        with self.assertRaises(ValueError):
            c.c = C(x=3)
