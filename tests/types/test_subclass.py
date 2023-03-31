import pickle
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from corgy.types import SubClass

from ._pklclasses import PklTestA, PklTestB


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
        with self.assertRaises(ValueError):
            type_("C")

    def test_subclass_raises_if_no_subclasses(self):
        class A:
            ...

        type_ = SubClass[A]
        with self.assertRaises(ValueError):
            type_("A")

    def test_subclass_raises_if_not_a_class(self):
        with self.assertRaises(TypeError):
            _ = SubClass[0]

    def test_subclass_accepts_base_iff_allow_base_set(self):
        class A:
            ...

        type_ = SubClass[A]
        with self.assertRaises(ValueError):
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

        class D(C):
            ...

        type_ = SubClass[A]
        self.assertIsInstance(type_("C")(), C)
        self.assertIsInstance(type_("D")(), D)

        type_.allow_indirect_subs = False
        with self.assertRaises(ValueError):
            type_("D")

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
            ...

        class B(A):  # pylint: disable=unused-variable
            def __init__(self, x):
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
        with self.assertRaises(ValueError):
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
        with self.assertRaises(ValueError):
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

    def test_subclass_which_property(self):
        class A:
            ...

        class B(A):
            ...

        class C(B):
            ...

        type_ = SubClass[A]
        init_b = type_("B")
        init_c = type_("C")

        self.assertEqual(init_b.which, B)
        self.assertEqual(init_c.which, C)

    def test_subclass_inst_pickleable(self):
        with TemporaryDirectory() as _tmpdir:
            _pkl_path = Path(_tmpdir) / "tmp.pkl"

            with _pkl_path.open("wb") as _f:
                pickle.dump(SubClass[PklTestA]("PklTestB"), _f)

            with _pkl_path.open("rb") as _f:
                _AT = pickle.load(_f)

            self.assertEqual(_AT, SubClass[PklTestA]("PklTestB"))

            _type = SubClass[PklTestA]
            _type.use_full_names = True
            b_full_name = PklTestB.__module__ + "." + PklTestB.__qualname__

            with _pkl_path.open("wb") as _f:
                pickle.dump(_type(b_full_name), _f)

            with _pkl_path.open("rb") as _f:
                _AT = pickle.load(_f)

            self.assertEqual(_AT, _type(b_full_name))
