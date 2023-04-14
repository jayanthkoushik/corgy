# pylint: disable=abstract-class-instantiated
import argparse
import sys
from argparse import (
    _StoreConstAction,
    _StoreFalseAction,
    _StoreTrueAction,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    ArgumentTypeError,
)
from collections.abc import Sequence as AbstractSequence
from io import BytesIO
from typing import ClassVar, List, Optional, Sequence, Set, Tuple
from unittest import skipIf, TestCase
from unittest.mock import MagicMock, patch

SequenceType = Sequence
TupleType = Tuple
SetType = Set
ListType = List

if sys.version_info >= (3, 9):
    from collections.abc import Sequence  # pylint: disable=reimported
    from typing import Annotated, Literal

    Tuple = tuple  # type: ignore
    Set = set  # type: ignore
    List = list  # type: ignore
else:
    from typing_extensions import Annotated, Literal

import corgy
from corgy import Corgy, CorgyHelpFormatter, corgyparser, NotRequired, Required
from corgy._actions import BooleanOptionalAction, OptionalTypeAction
from corgy._meta import CorgyMeta, get_concrete_collection_type

if sys.version_info >= (3, 11):
    import tomllib as tomli
else:
    try:
        import tomli
    except ImportError:
        tomli = None  # type: ignore

COLLECTION_TYPES = [Sequence, Tuple, Set, List]

if sys.version_info >= (3, 9):
    COLLECTION_TYPES.extend([SequenceType, TupleType, SetType, ListType])


def _get_collection_cast_type(_type) -> type:
    _cast_type = get_concrete_collection_type(_type)
    if _cast_type is AbstractSequence:
        return list
    return _cast_type  # type: ignore


class TestCorgyMeta(TestCase):
    @classmethod
    def setUpClass(cls):
        class _CorgyCls(Corgy):
            x1: Sequence[int]
            x2: Annotated[int, "x2 docstr"]
            x3: int = 3
            x4: Annotated[str, "x4 docstr"] = "4"

        cls._CorgyCls = _CorgyCls

    def test_corgy_cls_has_properties_from_type_hints(self):
        for _x in ["x1", "x2", "x3", "x4"]:
            with self.subTest(var=_x):
                self.assertTrue(hasattr(self._CorgyCls, _x))
                self.assertIsInstance(getattr(self._CorgyCls, _x), property)

    def test_corgy_cls_adds_hint_metadata_as_property_docstrings(self):
        for _x in ["x1", "x2", "x3", "x4"]:
            with self.subTest(var=_x):
                _x_prop = getattr(self._CorgyCls, _x)
                if _x in ["x1", "x3"]:
                    self.assertIsNone(_x_prop.__doc__)
                else:
                    self.assertEqual(_x_prop.__doc__, f"{_x} docstr")

    def test_corgy_cls_properties_have_correct_type_annotations(self):
        for _x, _type in zip(["x1", "x2", "x3", "x4"], [Sequence[int], int, int, str]):
            with self.subTest(var=_x):
                _x_prop = getattr(self._CorgyCls, _x)
                self.assertEqual(_x_prop.fget.__annotations__["return"], _type)

                self.assertEqual(
                    len(_x_prop.fget.__annotations__),
                    1,
                    f"spurious annotations: {_x_prop.fget.__annotations__}",
                )

                self.assertEqual(_x_prop.fset.__annotations__["val"], _type)
                self.assertEqual(
                    len(_x_prop.fset.__annotations__),
                    1,
                    f"spurious annotations: {_x_prop.fset.__annotations__}",
                )

    def test_corgy_cls_raises_if_help_annotation_not_str(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: Annotated[int, 1]

    def test_corgy_cls_raises_if_flags_not_list(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: Annotated[int, "x help", "x"]

    def test_corgy_cls_raises_if_flag_list_empty(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: Annotated[int, "x help", []]

    def test_corgy_cls_allows_dunder_defaults_as_attr_name(self):
        class C(Corgy):
            __defaults: int  # pylint: disable=unused-private-member
            x: int = 0

        self.assertTrue(hasattr(C, "__defaults"))
        self.assertIsInstance(getattr(C, "__defaults"), dict)
        self.assertTrue(hasattr(C, "_C__defaults"))
        self.assertIsInstance(getattr(C, "_C__defaults"), property)
        self.assertEqual(C().x, 0)

    def test_corgy_cls_raises_if_attr_name_is_dunder_another_attr(self):
        with self.assertRaises(TypeError):

            class _C(Corgy):  # pylint: disable=unused-variable
                x: int = 0
                __x = 2  # pylint: disable=unused-private-member

        with self.assertRaises(TypeError):

            class _C(Corgy):  # pylint: disable=unused-variable
                x: int
                __x: int  # pylint: disable=unused-private-member

    def test_corgy_cls_can_have_dunder_name(self):
        self.assertTrue(hasattr(self._CorgyCls, "_CorgyCls__x1"))

        class __C(Corgy):
            x: int

        self.assertTrue(hasattr(__C, "_C__x"))
        c = __C()
        c.x = 3
        self.assertEqual(c.x, 3)

    def test_corgy_cls_raises_on_setting_undefined_attribute(self):
        c = self._CorgyCls()
        with self.assertRaises(AttributeError):
            c.z = 0

    def test_corgy_cls_allows_custom_slots(self):
        class C(Corgy):
            __slots__ = ("y",)
            x: int

        c = C()
        c.y = 1
        self.assertEqual(c.y, 1)

    def test_corgy_cls_raises_on_slot_clash_with_attr(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: int
                __slots__ = ("__x",)

    def test_corgy_cls_allows_disabling_slots_modification(self):
        class C(Corgy, corgy_make_slots=False):
            x: int

        c = C()
        c.x = 1
        c.y = 2
        self.assertEqual(c.x, 1)
        self.assertEqual(c.y, 2)

    def test_corgy_cls_raises_if_slots_modification_disabled_with_custom_slots(self):
        with self.assertRaises(TypeError):

            class _(Corgy, corgy_make_slots=False):
                __slots__ = ("y",)
                x: int

    def test_corgy_cls_modifies_slots_if_explicitly_enabled(self):
        class C(Corgy, corgy_make_slots=True):
            __slots__ = ("y",)
            x: int

        c = C()
        c.x = 1
        c.y = 2
        self.assertEqual(c.x, 1)
        self.assertEqual(c.y, 2)
        with self.assertRaises(AttributeError):
            c.z = 3

    def test_corgy_cls_does_not_track_classvar(self):
        class C(Corgy):
            x: ClassVar[int] = 0

        self.assertEqual(C.x, 0)
        c = C()
        self.assertEqual(c.x, 0)
        with self.assertRaises(AttributeError):
            c.x = 1
        C.x = 1
        self.assertEqual(C.x, 1)
        self.assertEqual(c.x, 1)

    def test_corgy_cls_raises_if_classvar_has_no_value(self):
        with self.assertRaises(TypeError):

            class _(Corgy):
                x: ClassVar[int]

    def test_corgy_cls_raises_if_initialized_directly(self):
        with self.assertRaises(TypeError):
            Corgy()

    def test_corgy_cls_usable_without_annotations(self):
        class C(Corgy):
            ...

        c = C()
        self.assertEqual(repr(c), "C()")
        self.assertDictEqual(c.as_dict(), {})

    def test_corgy_cls_works_with_string_annotations(self):
        class C(Corgy):
            x1: "int"
            x2: "Annotated[str, 'x2 help']"
            x3: SequenceType["str"]

        for _x, _type in zip(["x1", "x2", "x3"], [int, str, SequenceType[str]]):
            with self.subTest(var=_x):
                self.assertIn(_x, C.attrs())
                self.assertEqual(C.attrs()[_x], _type)

        self.assertEqual(getattr(C, "__helps")["x2"], "x2 help")

    def test_corgy_instance_returns_correct_defaults(self):
        corgy_inst = self._CorgyCls()
        for _x, _d in zip(["x3", "x4"], [3, "4"]):
            with self.subTest(var=_x):
                _x_default = getattr(corgy_inst, _x)
                self.assertEqual(_x_default, _d)

    def test_corgy_instance_raises_on_unset_attr_access_without_default(self):
        corgy_inst = self._CorgyCls()
        for _x in ["x1", "x2"]:
            with self.subTest(var=_x):
                with self.assertRaises(AttributeError):
                    _x_default = getattr(corgy_inst, _x)

    def test_corgy_instance_attrs_can_be_unset_with_del(self):
        corgy_inst = self._CorgyCls(x2=1)
        self.assertEqual(corgy_inst.x2, 1)
        del corgy_inst.x2
        with self.assertRaises(AttributeError):
            _ = corgy_inst.x2
        self.assertIn("x2=<unset>", str(corgy_inst))

    def test_corgy_instance_attr_unset_handles_defaults(self):
        corgy_inst = self._CorgyCls()
        self.assertEqual(corgy_inst.x3, 3)
        del corgy_inst.x3
        with self.assertRaises(AttributeError):
            _ = corgy_inst.x3
        self.assertEqual(corgy_inst.x4, "4")
        corgy_inst.x4 = "5"
        self.assertEqual(corgy_inst.x4, "5")
        del corgy_inst.x4
        with self.assertRaises(AttributeError):
            _ = corgy_inst.x4

    def test_corgy_instance_raises_on_del_of_unset_attr(self):
        corgy_inst = self._CorgyCls()
        with self.assertRaises(AttributeError):
            del corgy_inst.x1

    def test_corgy_instance_raises_on_del_of_required_attr(self):
        class C(Corgy):
            x: Required[int]
            y: Required[int] = 2

        c = C(x=1, y=3)
        with self.assertRaises(TypeError):
            del c.x
        with self.assertRaises(TypeError):
            del c.y

    def test_corgy_cls_stores_required_attrs(self):
        class C(Corgy):
            x: Required[int]
            y: Required[int] = 1
            z: NotRequired[int]

        self.assertSetEqual(getattr(C, "__required"), {"x", "y"})

    def test_corgy_cls_handles_default_required(self):
        class C(Corgy, corgy_required_by_default=True):
            x: int
            y: Required[int]
            z: NotRequired[int]

        self.assertSetEqual(getattr(C, "__required"), {"x", "y"})

        class D(Corgy, corgy_required_by_default=False):
            x: int
            y: Required[int]
            z: NotRequired[int]

        self.assertSetEqual(getattr(D, "__required"), {"y"})


class TestCorgyClassInheritance(TestCase):
    def test_corgy_cls_inherits_annotations_by_default(self):
        class C:
            x1: int
            x3: "str"

        class D(Corgy, C):
            x2: int

        class CCorgy(Corgy):
            x1: int
            x3: "str"

        class DCorgy(CCorgy):
            x2: int

        for cls in (D, DCorgy):
            cls_attrs = cls.attrs()
            with self.subTest(cls=cls):
                self.assertIn("x1", cls_attrs)
                self.assertIn("x2", cls_attrs)
                self.assertIn("x3", cls_attrs)

    def test_corgy_cls_doesnt_inherit_annotations_if_disabled(self):
        class C:
            x1: int

        class D(Corgy, C, corgy_track_bases=False):
            x2: int

        class CCorgy(Corgy):
            x1: int

        class DCorgy(CCorgy, corgy_track_bases=False):
            x2: int

        for cls in (D, DCorgy):
            cls_attrs = cls.attrs()
            with self.subTest(cls=cls):
                self.assertIn("x2", cls_attrs)
                self.assertNotIn("x1", cls_attrs)

    def test_corgy_cls_inherits_annotations_from_ancestors(self):
        class C(Corgy):
            x1: int

        class D(C):
            x2: str

        class E1(D):
            x3: float

        class E2(D, corgy_track_bases=False):
            x3: float

        e1_attrs = E1.attrs()
        for _x, _type in zip(["x1", "x2", "x3"], [int, str, float]):
            with self.subTest(var=_x):
                self.assertIn(_x, e1_attrs)
                self.assertEqual(e1_attrs[_x], _type)

        e2_attrs = E2.attrs()
        self.assertNotIn("x1", e2_attrs)
        self.assertNotIn("x2", e2_attrs)
        self.assertIn("x3", e2_attrs)
        self.assertEqual(e2_attrs["x3"], float)

    def test_corgy_cls_overrides_inherited_annotations(self):
        class C:
            x1: int

        class D(Corgy, C):
            x1: str  # type: ignore

        class CCorgy(Corgy):
            x1: int

        class DCorgy(CCorgy):
            x1: str  # type: ignore

        for cls in (D, DCorgy):
            with self.subTest(cls=cls):
                self.assertEqual(cls.attrs()["x1"], str)

    def test_corgy_cls_subclass_works_without_annotations(self):
        class C(Corgy):
            x: int

        class D(C):
            ...

        self.assertTrue(hasattr(D, "x"))
        self.assertIsInstance(getattr(D, "x"), property)

    def test_corgy_cls_handles_inheritance_from_multiple_classes(self):
        class C:
            x1: int
            x2: str

        class D:
            x3: str

        class E(Corgy, C, D):
            ...

        e_attrs = E.attrs()
        self.assertIn("x1", e_attrs)
        self.assertIn("x2", e_attrs)
        self.assertIn("x3", e_attrs)

    def test_corgy_cls_inherits_group_annotations(self):
        class C:
            x: int

        class D:
            x: str
            c: C

        class E(Corgy, D):
            ...

        class CCorgy(Corgy):
            x: int

        class DCorgy(Corgy):
            x: str
            c: CCorgy

        class ECorgy(DCorgy):
            ...

        for cls, ccls in zip((E, ECorgy), (C, CCorgy)):
            cls_attrs = cls.attrs()
            with self.subTest(cls=cls):
                self.assertIn("c", cls_attrs)
                self.assertIs(cls_attrs["c"], ccls)

    def test_corgy_cls_inherits_defaults(self):
        class C:
            x1: int = 1

        class D(Corgy, C):
            ...

        class CCorgy(Corgy):
            x1: int = 1

        class DCorgy(CCorgy):
            ...

        for cls in (D, DCorgy):
            with self.subTest(cls=cls):
                self.assertIn("x1", getattr(cls, "__defaults"))

    def test_corgy_cls_overrides_inherited_defaults(self):
        class C:
            x1: int = 1
            x2: int = 2

        class D(Corgy, C):
            x1: int = 2
            x2: int

        class CCorgy(Corgy):
            x1: int = 1

        class DCorgy(CCorgy):
            x1: int = 2
            x2: int

        for cls in (D, DCorgy):
            with self.subTest(cls=cls):
                self.assertIn("x1", getattr(cls, "__defaults"))
                self.assertEqual(getattr(cls, "__defaults")["x1"], 2)
                self.assertNotIn("x2", getattr(cls, "__defaults"))

    def test_corgy_cls_inherits_classvar(self):
        class C:
            x: ClassVar[int] = 0
            y = 1
            __slots__ = ()

        class D(C, Corgy):
            z: ClassVar[str] = "0"

        class CCorgy(Corgy):
            x: ClassVar[int] = 0
            y = 1

        class DCorgy(CCorgy):
            z: ClassVar[str] = "0"

        for cls in (D, DCorgy):
            obj = cls()
            for _attr, _val in zip(("x", "y", "z"), (0, 1, "0")):
                with self.subTest(cls=cls.__name__, attr=_attr):
                    self.assertEqual(getattr(cls, _attr), _val)
                    self.assertEqual(getattr(obj, _attr), _val)
                    with self.assertRaises(AttributeError):
                        setattr(obj, _attr, "no")

    def test_corgy_cls_can_override_inherited_classvar(self):
        class C:
            x: ClassVar[int] = 0
            y = 1
            z: ClassVar[str] = "1"

        class D(C, Corgy):
            x: int  # type: ignore
            y: str = "1"
            z: ClassVar[str] = "2"

        class CCorgy(Corgy):
            x: ClassVar[int] = 0
            y = 1
            z: ClassVar[str] = "1"

        class DCorgy(CCorgy):
            x: int  # type: ignore
            y: str = "1"
            z: ClassVar[str] = "2"

        for ccls, dcls in zip((C, CCorgy), (D, DCorgy)):
            self.assertEqual(ccls.z, "1")
            self.assertEqual(dcls.z, "2")
            self.assertIsInstance(dcls.x, property)
            self.assertIsInstance(dcls.y, property)
            dobj = dcls()
            with self.assertRaises(AttributeError):
                _ = dobj.x
            self.assertEqual(dobj.y, "1")

    def test_corgy_cls_disabling_slots_does_not_interfere_with_inheritance(self):
        class C1(Corgy):
            x: int

        class C2(Corgy, corgy_make_slots=False):
            x: int

        class D1(C1, corgy_make_slots=False):
            y: int

        class D2(C2):
            y: int

        for cls in (D1, D2):
            d = cls()
            d.x = 1
            d.y = 2
            d.z = 3
            self.assertEqual(d.x, 1)
            self.assertEqual(d.y, 2)
            self.assertEqual(d.z, 3)

    def test_corgy_cls_inherits_required_attrs(self):
        class C(Corgy):
            x: Required[int]
            y: NotRequired[int]

        class D(C):
            w: Required[int]

        self.assertSetEqual(getattr(D, "__required"), {"x", "w"})

    def test_corgy_cls_overrides_inherited_required_attrs(self):
        class C(Corgy):
            x: Required[int]
            y: NotRequired[int]

        class D(C):
            x: NotRequired[int]

        self.assertSetEqual(getattr(D, "__required"), set())

    def test_corgy_cls_overrides_inherited_required_attr_with_default(self):
        class C(Corgy):
            x: Required[int]

        class D(C):
            x: int

        self.assertSetEqual(getattr(D, "__required"), set())

    def test_corgy_cls_handles_required_inheritance_from_non_corgy_cls(self):
        class C:
            x: Required[int]
            y: int

        class D1(C, Corgy, corgy_required_by_default=False):
            ...

        self.assertSetEqual(getattr(D1, "__required"), {"x"})

        class D2(C, Corgy, corgy_required_by_default=True):
            ...

        self.assertSetEqual(getattr(D2, "__required"), {"x", "y"})

        class D3(C, Corgy):
            x: NotRequired[int]
            y: Required[int]

        self.assertSetEqual(getattr(D3, "__required"), {"y"})


class TestCorgyTypeChecking(TestCase):
    def test_corgy_cls_type_checks_during_init(self):
        class C(Corgy):
            x: int

        with self.assertRaises(ValueError):
            C(x="1")

    def test_corgy_cls_type_checks_default_values(self):
        with self.assertRaises(ValueError):

            class _(Corgy):
                x: int = "1"

    def test_corgy_instance_raises_on_basic_type_mismatch(self):
        class C(Corgy):
            x: int

        c = C()
        with self.assertRaises(ValueError):
            c.x = "1"

    def test_corgy_instance_raises_on_coll_type_mismatch(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int]

                c = C()
                _test_val = [1] if _type in (Set, SetType) else {1}
                with self.assertRaises(ValueError):
                    c.x = _test_val

    def test_corgy_instance_allows_arbitray_sequence_type_for_simple_sequence(self):
        class C(Corgy):
            x: Sequence[int]

        c = C()
        for _val in [[1], (1,), (1, 2)]:
            with self.subTest(val=_val):
                c.x = _val

    def test_corgy_instance_allows_arbitrary_coll_for_empty_coll_type(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type

                c = C()
                _conc_type = _get_collection_cast_type(_type)
                for _val in [[1], ["1"], [1, "two", 3.0], []]:
                    _val = _conc_type(_val)
                    c.x = _val

    def test_corgy_instance_raises_on_coll_item_type_mismatch(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int]

                c = C()
                _conc_type = _get_collection_cast_type(_type)
                with self.assertRaises(ValueError):
                    c.x = _conc_type(["1"])
                with self.assertRaises(ValueError):
                    c.x = _conc_type([1, "1"])

    def test_corgy_instance_allows_empty_coll_for_simple_coll_type(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int]

                c = C()
                _conc_type = _get_collection_cast_type(_type)
                c.x = _conc_type()

    def test_corgy_instance_raises_on_empty_coll_with_ellipsis(self):
        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, SetType, ListType):
                continue
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int, ...]

                c = C()
                _conc_type = _get_collection_cast_type(_type)
                with self.assertRaises(ValueError):
                    c.x = _conc_type()

    def test_corgy_instance_raises_on_coll_length_mismatch(self):
        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, SetType, ListType):
                continue
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int, int]

                c = C()
                _conc_type = _get_collection_cast_type(_type)
                with self.assertRaises(ValueError):
                    c.x = _conc_type([1])
                with self.assertRaises(ValueError):
                    c.x = _conc_type([1, 1, 1])

    def test_corgy_instance_raises_on_fixed_length_sequence_item_type_mismatch(self):
        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, SetType, ListType):
                continue
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int, str, float]

                c = C()
                _conc_type = _get_collection_cast_type(_type)
                with self.assertRaises(ValueError):
                    c.x = _conc_type(["1", "1", 1.0])
                with self.assertRaises(ValueError):
                    c.x = _conc_type([1, 1, 1.0])
                with self.assertRaises(ValueError):
                    c.x = _conc_type([1, "1", "1"])

    def test_corgy_instance_raises_on_sub_coll_type_mismatch(self):
        class C(Corgy):
            x: Sequence[Set[int]]
            y: Set[Tuple[str, ...]]
            z: List[Tuple[int, str]]
            w: Tuple[List[int], ...]

        c = C()
        with self.assertRaises(ValueError):
            c.x = [{"1"}]
        with self.assertRaises(ValueError):
            c.x = [{1}, {"1"}]
        with self.assertRaises(ValueError):
            c.y = {tuple()}
        with self.assertRaises(ValueError):
            c.z = [(1, 1)]
        with self.assertRaises(ValueError):
            c.z = [(1, "1"), (1, 1)]
        with self.assertRaises(ValueError):
            c.z = [(1, "1"), [1, "1"]]
        with self.assertRaises(ValueError):
            c.w = ((1,),)
        with self.assertRaises(ValueError):
            c.w = ["1"]

    def test_corgy_instance_allows_none_for_optional_type(self):
        class C(Corgy):
            x: Optional[int]

        c = C()
        c.x = None

    def test_corgy_instance_allows_value_of_sub_type(self):
        class T:
            ...

        class Q(T):
            ...

        class C(Corgy):
            x: T

        c = C()
        c.x = Q()

    def test_corgy_instance_raises_on_assigning_out_of_set_to_literal(self):
        class C(Corgy):
            x: Literal[1, 2]

        c = C()
        with self.assertRaises(ValueError):
            c.x = 3

    def test_corgy_instance_accepts_values_specified_with_choices(self):
        class T:
            __choices__ = [1, "2"]

        class C(Corgy):
            x: T

        c = C()
        for _val in [1, "2"]:
            with self.subTest(val=_val):
                c.x = _val

    def test_corgy_instance_raises_on_assigning_out_of_set_to_type_with_choices(self):
        class T:
            __choices__ = [1, "2"]

        class C(Corgy):
            x: T

        c = C()
        with self.assertRaises(ValueError):
            c.x = 3

    def test_corgy_instance_raises_on_assigning_to_bare_literal(self):
        class C(Corgy):
            x: Literal

        c = C()
        with self.assertRaises(ValueError):
            c.x = 1


class TestCorgyInit(TestCase):
    def test_corgy_cls_init_assigns_values_to_attrs(self):
        class C(Corgy):
            x1: int
            x2: str

        c = C(x1=1, x2="2")
        self.assertEqual(c.x1, 1)
        self.assertEqual(c.x2, "2")

    def test_corgy_cls_init_ignores_unknown_attrs(self):
        class C(Corgy):
            x1: int
            x2: str

        c = C(x1=1, x2="2", x3=3)
        self.assertFalse(hasattr(c, "x3"))

    def test_corgy_cls_init_allows_missing_attrs(self):
        class C(Corgy):
            x1: int
            x2: str

        c = C(x1=1)
        self.assertEqual(c.x1, 1)
        with self.assertRaises(AttributeError):
            _ = c.x2

    def test_corgy_cls_init_handles_groups(self):
        class G(Corgy):
            x1: int
            x2: str

        class C(Corgy):
            x1: int
            g: G

        c = C(x1=10, g=G(x1=1, x2="2"))
        self.assertEqual(c.x1, 10)
        self.assertEqual(c.g.x1, 1)
        self.assertEqual(c.g.x2, "2")

    def test_corgy_cls_init_raises_if_required_attr_missing(self):
        class C(Corgy):
            x: Required[int]

        with self.assertRaises(ValueError):
            C()

    def test_corgy_cls_init_raises_if_required_group_missing(self):
        class G(Corgy):
            x: Required[int]

        class C(Corgy):
            g: Required[G]

        with self.assertRaises(ValueError):
            C()


class TestCorgyAttrs(TestCase):
    def test_corgy_cls_attrs_returns_dict_with_attr_types(self):
        class A(Corgy):
            x: int
            y: Sequence[str]

        self.assertDictEqual(A.attrs(), {"x": int, "y": Sequence[str]})

    def test_corgy_cls_attrs_strips_annotated(self):
        class A(Corgy):
            x: Annotated[int, "x"]

        self.assertDictEqual(A.attrs(), {"x": int})

    def test_corgy_cls_attrs_returns_empty_dict_if_no_attrs(self):
        class A(Corgy):
            ...

        self.assertDictEqual(A.attrs(), {})

    def test_corgy_cls_attrs_returns_group_types(self):
        class A(Corgy):
            ...

        class B(Corgy):
            a: A

        self.assertEqual(B.attrs(), {"a": A})

    def test_corgy_cls_attrs_includes_inherited_attrs(self):
        class A:
            x: int

        class B(Corgy, A):
            y: str

        self.assertEqual(B.attrs(), {"x": int, "y": str})


class TestCorgyAsDict(TestCase):
    @classmethod
    def setUpClass(cls):
        class _CorgyCls(Corgy):
            x1: Sequence[int]
            x2: Annotated[int, "x2 docstr"]
            x3: int = 3
            x4: Annotated[str, "x4 docstr"] = "4"

        cls._CorgyCls = _CorgyCls

    def test_as_dict_creates_dict_with_attr_values(self):
        c = self._CorgyCls(x1=[0, 1], x2=2, x3=30, x4="40")
        self.assertDictEqual(c.as_dict(), {"x1": [0, 1], "x2": 2, "x3": 30, "x4": "40"})

    def test_as_dict_uses_default_values(self):
        c = self._CorgyCls(x1=[0, 1], x2=2, x3=30)
        self.assertDictEqual(c.as_dict(), {"x1": [0, 1], "x2": 2, "x3": 30, "x4": "4"})

    def test_as_dict_ignores_unset_attrs_without_defaults(self):
        c = self._CorgyCls(x3=30, x4="40")
        self.assertDictEqual(c.as_dict(), {"x3": 30, "x4": "40"})

    def test_as_dict_adds_groups_directly_if_recursion_disabled(self):
        class D(Corgy):
            x: int
            c: self._CorgyCls

        c = self._CorgyCls()
        d = D(x=1, c=c)
        self.assertDictEqual(d.as_dict(recursive=False), {"x": 1, "c": c})

    def test_as_dict_ignores_flatten_if_recursion_disabled(self):
        class D(Corgy):
            x: int
            c: self._CorgyCls

        c = self._CorgyCls()
        d = D(x=1, c=c)
        self.assertDictEqual(d.as_dict(recursive=False, flatten=True), {"x": 1, "c": c})

    def test_as_dict_add_groups_as_dicts_by_default(self):
        class C(Corgy):
            x: int
            y: str

        class D(Corgy):
            x: int
            c: C

        class E(Corgy):
            x: int
            d: D

        e = E(x=1, d=D(x=10, c=C(x=100, y="100")))
        self.assertDictEqual(
            e.as_dict(), {"x": 1, "d": {"x": 10, "c": {"x": 100, "y": "100"}}}
        )

    def test_as_dict_flattens_groups_if_flatten_true(self):
        class C(Corgy):
            x: int
            y: str

        class D(Corgy):
            x: int
            c: C

        class E(Corgy):
            x: int
            d: D

        e = E(x=1, d=D(x=10, c=C(x=100, y="100")))
        self.assertDictEqual(
            e.as_dict(flatten=True), {"x": 1, "d:x": 10, "d:c:x": 100, "d:c:y": "100"}
        )

    def test_as_dict_with_flatten_is_inverted_by_from_dict(self):
        class C(Corgy):
            x: int
            y: str

        class D(Corgy):
            x: int
            c: C

        class E(Corgy):
            x: int
            d: D

        e1 = E(x=1, d=D(x=10, c=C(x=100, y="100")))
        e2 = E.from_dict(e1.as_dict(flatten=True))
        self.assertEqual(e2.x, e1.x)
        self.assertEqual(e2.d.x, e1.d.x)
        self.assertEqual(e2.d.c.x, e1.d.c.x)
        self.assertEqual(e2.d.c.y, e1.d.c.y)

    def test_as_dict_handles_groups_in_collections(self):
        class G(Corgy):
            x: int

        for _type in COLLECTION_TYPES:
            if _type in (Set, SetType):
                continue

            _cast_type = _get_collection_cast_type(_type)
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[G]

                gs = _cast_type([G(x=1), G(x=2)])
                c = C(x=gs)
                c_dict = c.as_dict(recursive=True)
                self.assertIs(type(c_dict["x"]), _cast_type)
                self.assertEqual(len(c_dict["x"]), 2)
                self.assertDictEqual(c_dict["x"][0], {"x": 1})
                self.assertDictEqual(c_dict["x"][1], {"x": 2})

                c = C(x=_cast_type())
                c_dict = c.as_dict(recursive=True)
                self.assertIs(type(c_dict["x"]), _cast_type)
                self.assertEqual(len(c_dict["x"]), 0)

    def test_as_dict_handles_flatten_in_nested_groups(self):
        class G1(Corgy):
            x: int

        class G2(Corgy):
            x: float
            g: G1

        class C(Corgy):
            g: Tuple[G2, ...]

        c = C(g=(G2(x=1.1, g=G1(x=11)), G2(x=2.2, g=G1(x=22))))
        self.assertEqual(
            c.as_dict(recursive=True, flatten=True),
            {"g": ({"x": 1.1, "g:x": 11}, {"x": 2.2, "g:x": 22})},
        )

    def test_as_dict_handles_nested_groups_in_collections(self):
        class G1(Corgy):
            x: int

        class G2(Corgy):
            x: Tuple[float, Sequence[G1], int]

        class C(Corgy):
            x: Tuple[G1, G2]

        c = C()
        c.x = (G1(), G2())
        c.x[0].x = 1
        c.x[1].x = (1.1, [G1(), G1(), G1()], 2)
        c.x[1].x[1][0].x = 10
        c.x[1].x[1][1].x = 20
        c.x[1].x[1][2].x = 30

        self.assertEqual(
            c.as_dict(recursive=True),
            {"x": ({"x": 1}, {"x": (1.1, [{"x": 10}, {"x": 20}, {"x": 30}], 2)})},
        )


class TestCorgyFromDict(TestCase):
    def test_cls_from_dict_creates_instance_from_dict(self):
        class C(Corgy):
            x: int
            y: str

        c = C.from_dict({"x": 1, "y": "two"})
        self.assertIsInstance(c, C)
        self.assertEqual(c.x, 1)
        self.assertEqual(c.y, "two")

    def test_cls_from_dict_handles_groups_as_dicts(self):
        class C(Corgy):
            x: int

        class D(Corgy):
            x: str
            c: C

        d = D.from_dict({"x": "two", "c": {"x": 1}})
        self.assertTrue(hasattr(d, "x"))
        self.assertEqual(d.x, "two")
        self.assertTrue(hasattr(d, "c"))
        self.assertTrue(hasattr(d.c, "x"))
        self.assertEqual(d.c.x, 1)

    def test_cls_from_dict_handles_groups_as_objects(self):
        class C(Corgy):
            x: int

        class D(Corgy):
            x: str
            c: C

        c = C(x=1)
        d = D.from_dict({"x": "two", "c": c})
        self.assertTrue(hasattr(d, "x"))
        self.assertEqual(d.x, "two")
        self.assertTrue(hasattr(d, "c"))
        self.assertIs(d.c, c)

    def test_cls_from_dict_handles_flat_group_args(self):
        class G(Corgy):
            x1: int
            x2: str

        class C(Corgy):
            x1: int
            g: G

        c = C.from_dict({"x1": 10, "g:x1": 1, "g:x2": "2"})
        self.assertEqual(c.x1, 10)
        self.assertEqual(c.g.x1, 1)
        self.assertEqual(c.g.x2, "2")

        c = C.from_dict({"x1": 10, "g:x1": 1})
        self.assertEqual(c.x1, 10)
        self.assertEqual(c.g.x1, 1)
        self.assertFalse(hasattr(c.g, "x2"))

    def test_cls_from_dict_handles_nested_groups(self):
        class G(Corgy):
            x1: int
            x2: str

        class H(Corgy):
            x1: int
            x2: str

        class C(Corgy):
            x1: int
            g: G
            h: H

        c = C.from_dict({"x1": 100, "g": G(x1=10, x2="20"), "h:x2": "2"})
        self.assertEqual(c.x1, 100)
        self.assertEqual(c.g.x1, 10)
        self.assertEqual(c.g.x2, "20")
        self.assertEqual(c.h.x2, "2")

    def test_cls_from_dict_raises_on_unknown_group_flat_args(self):
        class G(Corgy):
            x1: int
            x2: str

        class C(Corgy):
            x1: int
            g: G

        with self.assertRaises(ValueError):
            _ = C.from_dict({"gee:x1": 1})

    def test_cls_from_dict_raises_on_conflicting_group_args(self):
        class G(Corgy):
            x1: int
            x2: str

        class C(Corgy):
            x1: int
            g: G

        with self.assertRaises(ValueError):
            _ = C.from_dict({"g": G(x1=1), "g:x2": "2"})

    def test_cls_from_dict_raises_on_non_corgy_group(self):
        class C(Corgy):
            x: int

        with self.assertRaises(ValueError):
            C.from_dict({"x:": 1})
        with self.assertRaises(ValueError):
            C.from_dict({"x:x": 1})
        with self.assertRaises(ValueError):
            C.from_dict({"y:x": 1})

    def test_cls_from_dict_allows_dict_as_value(self):
        class D(Corgy):
            x: dict

        d = D.from_dict({"x": {"x": 1}})
        self.assertDictEqual(d.x, {"x": 1})

    def test_cls_from_dict_ignores_unknown_arguments(self):
        class C(Corgy):
            x: int

        C.from_dict({"x": 1, "y": {"x": 1}})

    def test_cls_from_dict_casts_values_when_try_cast_true(self):
        class C(Corgy):
            x: int

        c = C.from_dict({"x": "1"}, try_cast=True)
        self.assertEqual(c.x, 1)

    def test_cls_from_dict_handles_casting_coll_type(self):
        class C(Corgy):
            x: Tuple[int]

        c = C.from_dict({"x": [1, 2]}, try_cast=True)
        self.assertTupleEqual(c.x, (1, 2))

    def test_cls_from_dict_does_not_recast_sub_coll_type(self):
        class C(Corgy):
            x: Sequence[int]

        c = C.from_dict({"x": (1, 2)}, try_cast=True)
        self.assertTupleEqual(c.x, (1, 2))

    def test_cls_from_dict_casts_recursively(self):
        class C(Corgy):
            x: Tuple[Sequence[Optional[int]], Tuple[Optional[Tuple[float, ...]]]]

        c = C.from_dict({"x": [(1, "2", None), [None, ("1.0", 2.0)]]}, try_cast=True)
        self.assertEqual(c.x, ((1, 2, None), (None, (1.0, 2.0))))

    def test_cls_from_dict_cast_handles_bad_type(self):
        class T:
            def __init__(self, _):
                raise TypeError

        class C(Corgy):
            x: T
            y: Sequence[T]

        with self.assertRaises(ValueError):
            C.from_dict({"x": 1}, try_cast=True)
        with self.assertRaises(ValueError):
            C.from_dict({"y": 1}, try_cast=True)

    def test_cls_from_dict_handles_groups_in_collections(self):
        class G(Corgy):
            x: int

        for _type in COLLECTION_TYPES:
            if _type in (Set, SetType):
                continue

            _cast_type = _get_collection_cast_type(_type)
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[G]

                self.assertEqual(
                    C.from_dict({"x": _cast_type([G(x=1), G(x=2)])}),
                    C(x=_cast_type([G(x=1), G(x=2)])),
                )

                self.assertEqual(
                    C.from_dict({"x": _cast_type([{"x": 1}, {"x": 2}])}),
                    C(x=_cast_type([G(x=1), G(x=2)])),
                )

    def test_from_dict_handles_nested_groups_in_collections(self):
        class G1(Corgy):
            x: int

        class G2(Corgy):
            x: Tuple[float, Sequence[G1], int]

        class C(Corgy):
            x: Tuple[G1, G2]

        c = C()
        c.x = (G1(), G2())
        c.x[0].x = 1
        c.x[1].x = (1.1, [G1(), G1(), G1()], 2)
        c.x[1].x[1][0].x = 10
        c.x[1].x[1][1].x = 20
        c.x[1].x[1][2].x = 30

        self.assertEqual(
            c,
            C.from_dict(
                {"x": ({"x": 1}, {"x": (1.1, [{"x": 10}, {"x": 20}, {"x": 30}], 2)})}
            ),
        )

    def test_from_dict_raises_if_attr_missing_required(self):
        class C(Corgy):
            x: Required[int]

        with self.assertRaises(ValueError):
            C.from_dict({})

    def test_from_dict_handles_flat_groups_required(self):
        class G(Corgy):
            x: Required[int]

        class C(Corgy):
            x: Required[int]
            g: G

        self.assertEqual(C.from_dict({"x": 1, "g:x": 2}), C(x=1, g=G(x=2)))


class _LoadDictAsFromDictMeta(type):
    """Metaclass to create a version of `TestCorgyFromDict` for `load_dict`."""

    def __new__(cls, name, bases, namespace, **kwds):
        for _item in dir(bases[0]):
            if not _item.startswith("test_") or _item.endswith("_required"):
                continue
            test_fn = getattr(bases[0], _item)
            new_test_fn_name = _item.replace("from_dict", "load_dict")
            namespace[new_test_fn_name] = test_fn

        bases = (TestCase,)  # to prevent duplication of tests
        return super().__new__(cls, name, bases, namespace, **kwds)


class TestCorgyLoadDictIndirect(TestCorgyFromDict, metaclass=_LoadDictAsFromDictMeta):
    def setUp(self):
        def _load_as_from(cls, *args, **kwargs):
            c = cls()
            c.load_dict(*args, **kwargs)
            return c

        self._old_from_dict = Corgy.from_dict.__func__
        Corgy.from_dict = classmethod(_load_as_from)

    def tearDown(self):
        Corgy.from_dict = classmethod(self._old_from_dict)


class TestCorgyLoadDict(TestCase):
    def test_load_dict_preserves_existing_values(self):
        class C(Corgy):
            x: int
            y: str

        c = C(x=1)
        c.load_dict({"y": "two"})
        self.assertEqual(c, C(x=1, y="two"))

    def test_load_dict_unsets_existing_values_if_strict(self):
        class C(Corgy):
            x: int
            y: str

        c = C(x=1)
        c.load_dict({"y": "two"}, strict=True)
        self.assertEqual(c, C(y="two"))
        c = C()
        c.load_dict({"y": "two"}, strict=True)
        self.assertEqual(c, C(y="two"))

    def test_load_dict_loads_group_dicts(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        g = G(x=10)
        c = C(x=1, g=g)
        c.load_dict({"g": {"x": 20}})
        self.assertIs(c.g, g)
        self.assertEqual(c, C(x=1, g=G(x=20)))

    def test_load_dict_loads_flat_groups(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        g = G(x=10)
        c = C(x=1, g=g)
        c.load_dict({"g:x": 20})
        self.assertIs(c.g, g)
        self.assertEqual(c, C(x=1, g=G(x=20)))

    def test_load_dict_raises_on_group_clash(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        g = G(x=10)
        c = C(x=1, g=g)
        with self.assertRaises(ValueError):
            c.load_dict({"g": {"x": 20}, "g:x": 20})
        with self.assertRaises(ValueError):
            c.load_dict({"gee:x": 10})
        with self.assertRaises(ValueError):
            c.load_dict({"x:x": 10})

    def test_load_dict_loads_groups_directly(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        g = G(x=10)
        c = C(x=1, g=g)
        c.load_dict({"g": G(x=20)})
        self.assertIsNot(c.g, g)
        self.assertEqual(c, C(x=1, g=G(x=20)))

    def test_load_dict_unsets_group_if_strict(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        g = G(x=10)
        c = C(x=1, g=g)
        c.load_dict({"x": 2}, strict=True)
        self.assertEqual(c, C(x=2))

    def test_load_dict_raises_if_unsetting_required_attr(self):
        class C(Corgy):
            x: Required[int]

        c = C(x=1)
        with self.assertRaises(TypeError):
            c.load_dict({}, strict=True)


class TestCorgyPrinting(TestCase):
    @classmethod
    def setUpClass(cls):
        class _CorgyCls(Corgy):
            x1: Sequence[int]
            x2: Annotated[int, "x2 docstr"]
            x3: int = 3
            x4: Annotated[str, "x4 docstr"] = "4"

        cls._CorgyCls = _CorgyCls

    def test_corgy_instance_has_correct_repr_str(self):
        c = self._CorgyCls()
        c.x1 = [0, 1]
        c.x2 = 2
        c.x4 = "8"
        self.assertEqual(repr(c), "_CorgyCls(x1=[0, 1], x2=2, x3=3, x4='8')")
        self.assertEqual(str(c), "_CorgyCls(x1=[0, 1], x2=2, x3=3, x4=8)")

    def test_corgy_instance_repr_str_handles_unset_values(self):
        c = self._CorgyCls()
        self.assertEqual(repr(c), "_CorgyCls(x3=3, x4='4')")
        self.assertEqual(str(c), "_CorgyCls(x1=<unset>, x2=<unset>, x3=3, x4=4)")

    def test_corgy_instance_repr_str_handles_groups(self):
        class D(Corgy):
            x: int
            c: self._CorgyCls

        d = D(x=1, c=self._CorgyCls(x1=[0, 1], x2=2, x4="8"))
        self.assertEqual(repr(d), "D(x=1, c=_CorgyCls(x1=[0, 1], x2=2, x3=3, x4='8'))")
        self.assertEqual(str(d), "D(x=1, c=_CorgyCls(x1=[0, 1], x2=2, x3=3, x4=8))")

    def test_corgy_instance_repr_eval_is_instance(self):
        class C(Corgy):
            x: Sequence[int]
            y: str = "one"

        class D(Corgy):
            x: int
            c: C

        d1 = D(x=1, c=C(x=[0, 1]))
        d2 = eval(repr(d1))  # pylint: disable=eval-used
        self.assertEqual(d2.x, d1.x)
        self.assertEqual(d2.c.y, d1.c.y)
        self.assertListEqual(d2.c.x, d1.c.x)


class TestCorgyAddArgsToParser(TestCase):
    def setUp(self):
        self.parser = ArgumentParser()
        self.parser.add_argument = MagicMock()
        self.parser.add_argument_group = MagicMock()

    @classmethod
    def setUpClass(cls):
        # Patch `CorgyMeta.__new__` to make `corgy_required_by_default` `True` if
        # not specified.
        _old_new = CorgyMeta.__new__

        def _new(cls, name, bases, namespace, **kwargs):
            if "corgy_required_by_default" not in kwargs:
                kwargs["corgy_required_by_default"] = True
            return _old_new(cls, name, bases, namespace, **kwargs)

        cls._new_patcher = patch.object(CorgyMeta, "__new__", _new)
        cls._new_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._new_patcher.stop()

    def test_add_args_raises_if_custom_flags_on_group(self):
        with self.assertRaises(TypeError):

            class G(Corgy):
                x: int

            class _(Corgy):
                g: Annotated[G, "group G", ["-g", "--grp"]]

    def test_add_args_replaces_underscores_with_hyphens(self):
        class C(Corgy):
            the_x_arg: int

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--the-x-arg", type=int, required=True
        )

    def test_add_args_handles_provided_prefix(self):
        class C(Corgy):
            the_x_arg: int

        C.add_args_to_parser(self.parser, "prefix")
        self.parser.add_argument.assert_called_once_with(
            "--prefix:the-x-arg", type=int, required=True
        )

    def test_add_args_handles_custom_metavar(self):
        class T:
            __metavar__ = "T"

        class C(Corgy):
            x: T

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=T, required=True, metavar="T"
        )

    def test_add_args_handles_plain_type_annotation(self):
        class C(Corgy):
            x: int

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, required=True)

    def test_add_args_handles_default_value(self):
        class C(Corgy):
            x: int = 0

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, default=0)

    def test_add_args_handles_annotated_optional(self):
        class C(Corgy):
            x: Optional[int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, action=OptionalTypeAction, required=True
        )

    @skipIf(sys.version_info < (3, 10), "`|` syntax needs Python 3.10 or higher")
    def test_add_args_handles_annotated_new_style_optional(self):
        class C(Corgy):
            x: int | None  # type: ignore # pylint: disable=unsupported-binary-operation

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, action=OptionalTypeAction, required=True
        )

    def test_add_args_handles_annotated_optional_with_default(self):
        class C(Corgy):
            x: Optional[int] = 0

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, action=OptionalTypeAction, default=0
        )

    def test_add_args_uses_metadata_as_help(self):
        class C(Corgy):
            x: Annotated[int, "x docstring"]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, required=True, help="x docstring"
        )

    def test_add_args_handles_custom_flag(self):
        class C(Corgy):
            the_x_arg: Annotated[int, "x help", ["-x", "--the-x", "--the-x-arg"]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "-x",
            "--the-x",
            "--the-x-arg",
            type=int,
            required=True,
            help="x help",
            dest="the_x_arg",
        )

    def test_add_args_uses_positional_flag(self):
        class C(Corgy):
            the_x_arg: Annotated[int, "x help", ["x"]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "the_x_arg", type=int, help="x help"
        )

    def test_add_handles_positional_flag_with_same_name(self):
        class C(Corgy):
            the_x_arg: Annotated[int, "x help", ["the-x-arg"]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "the_x_arg", type=int, help="x help"
        )

    def test_add_handles_positional_optional(self):
        class C(Corgy):
            the_x_arg: Annotated[Optional[int], "x help", ["the-x-arg"]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "the_x_arg", type=int, help="x help", action=OptionalTypeAction
        )

    def test_add_args_converts_literal_to_choices(self):
        class C(Corgy):
            x: Literal[1, 2, 3]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, required=True, choices=(1, 2, 3)
        )

    def test_add_args_raises_if_choices_not_same_type(self):
        class C(Corgy):
            x: Literal[1, 2, "3"]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)

    def test_add_args_uses_base_class_for_choice_type(self):
        class A:
            ...

        class A1(A):
            ...

        class A2(A):
            ...

        class B:
            ...

        class B1(B):
            ...

        class BA1(B, A2):
            ...

        class C(Corgy):
            x: Literal[A1, A2, BA1]  # type: ignore

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=A, required=True, choices=(A1, A2, BA1)
        )

        with self.assertRaises(TypeError):

            class D(Corgy):
                x: Literal[A1, A2, B1]  # type: ignore

            D.add_args_to_parser(self.parser)

    def test_add_args_uses_custom_choices(self):
        class A:
            __choices__ = (1, 2, 3)

        class C(Corgy):
            x: A

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=A, required=True, choices=(1, 2, 3)
        )

    def test_add_args_uses_store_const_action_for_single_choice_literal(self):
        class A:
            __choices__ = (42,)

        for type_ in (A, Literal[42]):
            with self.subTest(type=type_):

                class C(Corgy):
                    x: type_

                self.setUp()
                C.add_args_to_parser(self.parser)
                self.parser.add_argument.assert_called_once_with(
                    "--x", action=_StoreConstAction, const=42, required=True
                )

    def test_add_args_uses_store_true_false_action_for_true_false_literal(self):
        for val in (True, False):

            class A:
                __choices__ = (val,)

            for type_ in (A, Literal[val]):  # type: ignore
                with self.subTest(val=val, type=type_):

                    class C(Corgy):
                        x: type_

                    self.setUp()
                    C.add_args_to_parser(self.parser)
                    self.parser.add_argument.assert_called_once_with(
                        "--x",
                        action=(_StoreTrueAction if val else _StoreFalseAction),
                        required=True,
                    )

    def test_add_args_handles_user_defined_class_as_type(self):
        class T:
            ...

        class C(Corgy):
            x: T

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=T, required=True)

    def test_add_args_handles_user_defined_object_as_default(self):
        class T:
            ...

        t = T()

        class C(Corgy):
            x: T = t

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=T, default=t)

    def test_add_args_converts_bool_to_action(self):
        class C(Corgy):
            x: bool

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, action=BooleanOptionalAction, required=True
        )

    def test_add_args_handles_default_for_bool_type(self):
        class C(Corgy):
            x: bool = False

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, action=BooleanOptionalAction, default=False
        )

    def test_add_args_does_not_convert_bool_coll_to_action(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[bool]

                self.setUp()
                C.add_args_to_parser(self.parser)
                self.parser.add_argument.assert_called_once_with(
                    "--x", type=bool, required=True, nargs="*"
                )

    def test_add_args_does_not_convert_bool_choices_to_action(self):
        class C(Corgy):
            x: Literal[True, False]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, required=True, choices=(True, False)
        )

    def test_add_args_handles_positional_bool(self):
        class C(Corgy):
            x: Annotated[bool, "x help", ["x"]]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("x", type=bool, help="x help")

    def test_add_args_raises_if_coll_has_no_types(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type

                self.setUp()
                with self.assertRaises(TypeError):
                    C.add_args_to_parser(self.parser)

    def test_add_args_sets_nargs_to_asterisk_for_coll_type(self):
        for _type in COLLECTION_TYPES:
            if _type is not ListType:
                continue

            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int]

                self.setUp()
                C.add_args_to_parser(self.parser)
                self.parser.add_argument.assert_called_once_with(
                    "--x", type=int, required=True, nargs="*"
                )

    def test_add_args_handles_optional_coll_type(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: Optional[_type[int]]

                self.setUp()
                C.add_args_to_parser(self.parser)
                self.parser.add_argument.assert_called_once_with(
                    "--x", type=int, nargs="*", action=OptionalTypeAction, required=True
                )

    def test_add_args_sets_nargs_to_plus_for_non_empty_sequence_type(self):
        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, ListType, SetType):
                continue

            class C(Corgy):
                x: _type[int, ...]

            self.setUp()
            C.add_args_to_parser(self.parser)
            self.parser.add_argument.assert_called_once_with(
                "--x", type=int, nargs="+", required=True
            )

    def test_add_args_handles_coll_with_default(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):
                _conc_type = _get_collection_cast_type(_type)

                class C(Corgy):
                    x: _type[int] = _conc_type([1, 2, 3])

                self.setUp()
                C.add_args_to_parser(self.parser)
                self.parser.add_argument.assert_called_once_with(
                    "--x", type=int, nargs="*", default=_conc_type([1, 2, 3])
                )

    def test_add_args_converts_literal_coll_to_choices_with_nargs(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[Literal[1, 2, 3]]

                self.setUp()
                C.add_args_to_parser(self.parser)
                self.parser.add_argument.assert_called_once_with(
                    "--x", type=int, nargs="*", required=True, choices=(1, 2, 3)
                )

    def test_add_args_handles_fixed_length_sequence_with_choices(self):
        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, SetType, ListType):
                continue

            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[Literal[1, 2, 3], Literal[1, 2, 3]]

                self.setUp()
                C.add_args_to_parser(self.parser)
                self.parser.add_argument.assert_called_once_with(
                    "--x", type=int, nargs=2, required=True, choices=(1, 2, 3)
                )

    def test_add_args_raises_if_fixed_length_coll_choices_not_all_same(self):
        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, SetType, ListType):
                continue

            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[Literal[1, 2, 3], Literal[1, 2]]

                self.setUp()
                with self.assertRaises(TypeError):
                    C.add_args_to_parser(self.parser)

    def test_add_args_handles_fixed_length_typed_sequence(self):
        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, SetType, ListType):
                continue

            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int, int, int]

                self.setUp()
                C.add_args_to_parser(self.parser)
                self.parser.add_argument.assert_called_once_with(
                    "--x", type=int, nargs=3, required=True
                )

    def test_add_args_raises_if_fixed_length_sequence_types_not_all_same(self):
        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, SetType, ListType):
                continue

            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int, str, int]

                self.setUp()
                with self.assertRaises(TypeError):
                    C.add_args_to_parser(self.parser)

    def test_add_args_converts_corgy_attr_to_argument_group(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            g: Annotated[G, "group G"]

        grp_parser = MagicMock()
        self.parser.add_argument_group = MagicMock(return_value=grp_parser)

        C.add_args_to_parser(self.parser)
        self.parser.add_argument_group.assert_called_once_with("g", "group G")
        grp_parser.add_argument.assert_called_once_with(
            "--g:x", type=int, required=True
        )

    def test_add_args_allows_repeated_name_in_group(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, required=True)
        self.parser.add_argument_group.assert_called_once_with("g", None)

    def test_add_args_handles_custom_flags_inside_group(self):
        class G(Corgy):
            the_x_arg: Annotated[int, "x help", ["-x", "--the-x", "--the-x-arg"]]

        class C(Corgy):
            the_grp: G

        grp_parser = MagicMock()
        self.parser.add_argument_group.return_value = grp_parser

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_not_called()
        self.parser.add_argument_group.assert_called_once_with("the_grp", None)
        grp_parser.add_argument.assert_called_once_with(
            "--the-grp:x",
            "--the-grp:the-x",
            "--the-grp:the-x-arg",
            type=int,
            help="x help",
            required=True,
            dest="the_grp:the_x_arg",
        )

    def test_add_args_handles_custom_flags_of_positional_args_inside_group(self):
        class G(Corgy):
            the_x_arg: Annotated[int, "x help", ["x", "the-x", "the_x_arg"]]

        grp_parser = ArgumentParser()
        grp_parser.add_argument = MagicMock()
        G.add_args_to_parser(grp_parser)
        grp_parser.add_argument.assert_called_once_with(
            "the_x_arg", type=int, help="x help"
        )

        class C(Corgy):
            the_grp: G

        grp_parser = MagicMock()
        self.parser.add_argument_group.return_value = grp_parser

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_not_called()
        self.parser.add_argument_group.assert_called_once_with("the_grp", None)
        grp_parser.add_argument.assert_called_once_with(
            "--the-grp:x",
            "--the-grp:the-x",
            "--the-grp:the_x_arg",
            type=int,
            help="x help",
            required=True,
            dest="the_grp:the_x_arg",
        )

    def test_add_args_makes_nested_groups_flat(self):
        class G2(Corgy):
            x: int

        class G1(Corgy):
            x: int
            g2: G2

        class C(Corgy):
            x: int
            g1: G1

        grp_parser = MagicMock()
        self.parser.add_argument_group.return_value = grp_parser

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, required=True)
        self.parser.add_argument_group.assert_any_call("g1", None)
        grp_parser.add_argument.assert_has_calls(
            [
                (("--g1:x",), {"type": int, "required": True}),
                (("--g1:g2:x",), {"type": int, "required": True}),
            ]
        )

    def test_add_args_handles_flatten_subgrps_arg(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        C.add_args_to_parser(self.parser, flatten_subgrps=True)
        self.parser.add_argument.assert_has_calls(
            [
                (("--x",), {"type": int, "required": True}),
                (("--g:x",), {"type": int, "required": True}),
            ]
        )

    def test_add_args_infers_correct_base_type_from_complex_type_hint(self):
        class C(Corgy):
            x: Annotated[Optional[Sequence[str]], "x"]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x",
            type=str,
            help="x",
            nargs="*",
            action=OptionalTypeAction,
            required=True,
        )

    def test_add_args_allows_function_base_type(self):
        def f(x: str) -> int:
            return int(x)

        class C(Corgy):
            x: f

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=f, required=True)

    def test_add_args_handles_passed_defaults(self):
        class C(Corgy):
            x: int

        C.add_args_to_parser(self.parser, defaults={"x": 42})
        self.parser.add_argument.assert_called_once_with("--x", type=int, default=42)

    def test_add_args_overrides_default_values_with_passed_defaults(self):
        class C(Corgy):
            x: int = 0

        C.add_args_to_parser(self.parser, defaults={"x": 42})
        self.parser.add_argument.assert_called_once_with("--x", type=int, default=42)

    def test_add_args_handles_passed_defaults_for_groups(self):
        class G(Corgy):
            x: int = 1
            y: str
            z: float = 2.0
            w: int

        class C(Corgy):
            g: G

        grp_parser = MagicMock()
        self.parser.add_argument_group.return_value = grp_parser

        C.add_args_to_parser(self.parser, defaults={"g": G(x=42, y="foo", w=-1)})
        grp_parser.add_argument.assert_has_calls(
            [
                (("--g:x",), {"type": int, "default": 42}),
                (("--g:y",), {"type": str, "default": "foo"}),
                (("--g:z",), {"type": float, "default": 2.0}),
                (("--g:w",), {"type": int, "default": -1}),
            ],
            any_order=True,
        )

    def test_add_args_handles_individually_passed_defaults_for_groups(self):
        class G(Corgy):
            x: int = 1
            y: str
            z: float = 2.0
            w: int

        class C(Corgy):
            g: G

        grp_parser = MagicMock()
        self.parser.add_argument_group.return_value = grp_parser

        C.add_args_to_parser(
            self.parser, defaults={"g": G(x=42, y="foo", w=-1), "g:x": 43, "g:w": 44}
        )
        grp_parser.add_argument.assert_has_calls(
            [
                (("--g:x",), {"type": int, "default": 43}),
                (("--g:y",), {"type": str, "default": "foo"}),
                (("--g:z",), {"type": float, "default": 2.0}),
                (("--g:w",), {"type": int, "default": 44}),
            ],
            any_order=True,
        )

    def test_add_args_raises_if_passed_defaults_for_unknown_attr(self):
        class C(Corgy):
            x: int

        with self.assertRaises(ValueError):
            C.add_args_to_parser(self.parser, defaults={"y": 42})

    def test_add_args_raises_if_passed_defaults_for_unknown_group_attr(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        with self.assertRaises(ValueError):
            C.add_args_to_parser(self.parser, defaults={"g:y": 42})

    def test_add_args_raises_if_passed_non_corgy_as_group_default(self):
        class G(Corgy):
            x: int

        class C(Corgy):
            x: int
            g: G

        with self.assertRaises(ValueError):
            C.add_args_to_parser(self.parser, defaults={"g": 42})

    def test_add_args_handles_inherited_arguments(self):
        class C:
            x: int

        class D(Corgy, C):
            y: str

        class CCorgy(Corgy):
            x: int

        class DCorgy(CCorgy):
            y: str

        for cls in (D, DCorgy):
            self.parser.add_argument = MagicMock()
            cls.add_args_to_parser(self.parser)
            self.parser.add_argument.assert_has_calls(
                [
                    (("--x",), {"type": int, "required": True}),
                    (("--y",), {"type": str, "required": True}),
                ],
                any_order=True,
            )

    def test_add_args_handles_inheritance_disabling(self):
        class C:
            x: int

        class D(Corgy, C, corgy_track_bases=False):
            y: str

        class CCorgy(Corgy):
            x: int

        class DCorgy(CCorgy, corgy_track_bases=False):
            y: str

        for cls in (D, DCorgy):
            self.parser.add_argument = MagicMock()
            cls.add_args_to_parser(self.parser)
            self.parser.add_argument.assert_called_once_with(
                "--y", type=str, required=True
            )

    def test_add_args_uses_inherited_defaults(self):
        class C:
            x: int = 2

        class D(Corgy, C):
            ...

        class CCorgy(Corgy):
            x: int = 2

        class DCorgy(CCorgy):
            ...

        for cls in (D, DCorgy):
            self.parser.add_argument = MagicMock()
            cls.add_args_to_parser(self.parser)
            self.parser.add_argument.assert_called_once_with("--x", type=int, default=2)

    def test_add_args_uses_inherited_help_and_flags(self):
        class C(Corgy):
            the_x_arg: Annotated[int, "x help", ["-x", "--the-x", "--the-x-arg"]]

        class D(C):
            ...

        D.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "-x",
            "--the-x",
            "--the-x-arg",
            type=int,
            required=True,
            help="x help",
            dest="the_x_arg",
        )

    def test_add_args_raises_on_inconsistent_flags(self):
        class C(Corgy):
            x: Annotated[int, "x help", ["-x", "the-x"]]

        with self.assertRaises(TypeError):
            C.add_args_to_parser(self.parser)


class TestCorgyAddRequiredArgsToParser(TestCase):
    def setUp(self):
        self.parser = ArgumentParser()
        self.parser.add_argument = MagicMock()
        self.parser.add_argument_group = MagicMock()

    def test_add_args_sets_required_true_for_required_attrs(self):
        class C(Corgy):
            x: Required[int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, required=True)

    def test_add_args_doesnt_set_default_suppress_for_optional_attrs(self):
        class C(Corgy):
            x: NotRequired[int]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=int, default=argparse.SUPPRESS
        )

    def test_add_args_handles_defaults_for_required_attrs(self):
        class C(Corgy):
            x: Required[int] = 1

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, default=1)

    def test_add_args_handles_defaults_for_optional_attrs(self):
        class C(Corgy):
            x: NotRequired[int] = 1

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with("--x", type=int, default=1)

    def test_add_args_handles_optional_bool(self):
        class C(Corgy):
            x: NotRequired[bool]

        C.add_args_to_parser(self.parser)
        self.parser.add_argument.assert_called_once_with(
            "--x", type=bool, action=BooleanOptionalAction, default=argparse.SUPPRESS
        )


class TestCorgyCmdlineParsing(TestCase):
    def setUp(self):
        self.parser = ArgumentParser()
        self.orig_parse_args = ArgumentParser.parse_args

    def test_cmdline_args_are_parsed_to_corgy_cls_properties(self):
        class C(Corgy):
            x: int
            y: str
            z: Sequence[int]

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "1", "--y", "2", "--z", "3", "4"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.x, 1)
        self.assertEqual(c.y, "2")
        self.assertListEqual(c.z, [3, 4])

    def test_cmdline_args_are_parsed_with_custom_flags(self):
        class C(Corgy):
            var: Annotated[int, "x help", ["-x", "--the-x", "--the-x-arg"]]

        for flag in ["-x", "--the-x", "--the-x-arg"]:
            with self.subTest(flag=flag):
                self.parser = ArgumentParser()
                self.parser.parse_args = lambda: self.orig_parse_args(
                    self.parser, ["-x", "1"]
                )
                c = C.parse_from_cmdline(self.parser)
                self.assertEqual(c.var, 1)

    def test_cmdline_positional_args_are_parsed_with_custom_flags(self):
        class C(Corgy):
            var: Annotated[int, "x help", ["x"]]

        self.parser = ArgumentParser()
        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["1"])
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.var, 1)

    def test_cmdline_positional_optional_args_are_pared_without_value(self):
        class C(Corgy):
            var: Annotated[Optional[int], "x help", ["x"]]

        for args in [[], ["1"]]:
            with self.subTest(args=args):
                self.parser = ArgumentParser()
                # pylint: disable=cell-var-from-loop
                self.parser.parse_args = lambda: self.orig_parse_args(self.parser, args)
                c = C.parse_from_cmdline(self.parser)
                if not args:
                    self.assertIsNone(c.var)
                else:
                    self.assertEqual(c.var, 1)

    def test_cmdline_parsing_handles_group_arguments(self):
        class G(Corgy):
            x: int
            y: str

        class C(Corgy):
            x: int
            y: int
            g: G

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "1", "--y", "2", "--g:x", "3", "--g:y", "four"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.x, 1)
        self.assertEqual(c.y, 2)
        self.assertEqual(c.g.x, 3)
        self.assertEqual(c.g.y, "four")

    def test_cmdline_parsing_handles_groups_with_positional_args(self):
        class G(Corgy):
            the_x_var: Annotated[int, "x help", ["x", "the_x", "the-x-var"]]

        grp_parser = ArgumentParser()
        grp_parser.parse_args = lambda: self.orig_parse_args(grp_parser, ["1"])
        g = G.parse_from_cmdline(grp_parser)
        self.assertEqual(g.the_x_var, 1)

        class C(Corgy):
            x: int
            g: G

        for grp_flag in ["--g:x", "--g:the-x", "--g:the-x-var"]:
            with self.subTest(grp_flag=grp_flag):
                self.setUp()
                self.parser.parse_args = lambda: self.orig_parse_args(
                    self.parser,
                    ["--x", "1", grp_flag, "2"],  # pylint: disable=cell-var-from-loop
                )
                c = C.parse_from_cmdline(self.parser)
                self.assertEqual(c.x, 1)
                self.assertEqual(c.g.the_x_var, 2)

    def test_cmdline_parsing_handles_nested_groups(self):
        class G1(Corgy):
            x: int

        class G2(Corgy):
            x: int
            g: G1

        class C(Corgy):
            x: int
            g1: G1
            g2: G2

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "1", "--g1:x", "2", "--g2:x", "3", "--g2:g:x", "4"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.x, 1)
        self.assertEqual(c.g1.x, 2)
        self.assertEqual(c.g2.x, 3)
        self.assertEqual(c.g2.g.x, 4)

    def test_cmdline_parsing_handles_nested_groups_with_custom_flags(self):
        class G1(Corgy):
            var: Annotated[int, "var help", ["-v", "--var"]]

        class G2(Corgy):
            var: Annotated[int, "var help", ["-v", "--var"]]
            g: G1

        class C(Corgy):
            var: Annotated[int, "var help", ["-v", "--var"]]
            g1: G1
            g2: G2

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["-v", "1", "--g1:v", "2", "--g2:var", "3", "--g2:g:v", "4"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.var, 1)
        self.assertEqual(c.g1.var, 2)
        self.assertEqual(c.g2.var, 3)
        self.assertEqual(c.g2.g.var, 4)

    def test_cmdline_parsing_handles_custom_base_type(self):
        class A:
            def __init__(self, s):
                x, y = s.split(",")
                self.x = int(x)
                self.y = float(y)

        class C(Corgy):
            a: A

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--a", "1,2.3"]
        )
        c = C.parse_from_cmdline(self.parser)
        self.assertEqual(c.a.x, 1)
        self.assertEqual(c.a.y, 2.3)

    def test_parse_from_cmdline_passes_extra_args_to_parser_constructor(self):
        class C(Corgy):
            x: int

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["--x", "1"])
        with patch("corgy._corgy.ArgumentParser", MagicMock(return_value=self.parser)):
            C.parse_from_cmdline(
                formatter_class=ArgumentDefaultsHelpFormatter, add_help=False
            )
            corgy._corgy.ArgumentParser.assert_called_once_with(
                formatter_class=ArgumentDefaultsHelpFormatter, add_help=False
            )

    def test_parse_from_cmdline_uses_corgy_help_formatter_if_no_formatter_specified(
        self,
    ):
        class C(Corgy):
            x: int

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["--x", "1"])
        with patch("corgy._corgy.ArgumentParser", MagicMock(return_value=self.parser)):
            C.parse_from_cmdline(add_help=False)
            corgy._corgy.ArgumentParser.assert_called_once_with(
                formatter_class=CorgyHelpFormatter, add_help=False
            )

    def test_parse_from_cmdline_ignores_extra_arguments(self):
        class C(Corgy):
            x: int

        self.parser.add_argument("--y", type=str)
        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "1", "--y", "2"]
        )
        c = C.parse_from_cmdline(self.parser, add_help=False)
        self.assertEqual(c.x, 1)
        with self.assertRaises(AttributeError):
            _ = c.y

    def test_parse_from_cmdline_handles_passed_defaults(self):
        class C(Corgy):
            x: int

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, [])
        c = C.parse_from_cmdline(self.parser, defaults={"x": 1}, add_help=False)
        self.assertEqual(c.x, 1)

    def test_parse_from_cmdline_handles_bools(self):
        class C(Corgy):
            x: bool
            y: bool

        self.parser.parse_args = lambda: self.orig_parse_args(
            self.parser, ["--x", "--no-y"]
        )
        c = C.parse_from_cmdline(self.parser, add_help=False)
        self.assertEqual(c.x, True)
        self.assertEqual(c.y, False)

    def test_parse_from_cmdline_handles_colls(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int]

                self.setUp()
                self.parser.parse_args = lambda: self.orig_parse_args(
                    self.parser, ["--x", "1", "2"]
                )
                c = C.parse_from_cmdline(self.parser, add_help=False)
                if _type in (Tuple, TupleType):
                    self.assertTupleEqual(c.x, (1, 2))
                elif _type in (Set, SetType):
                    self.assertSetEqual(c.x, {1, 2})
                else:
                    self.assertListEqual(c.x, [1, 2])

    def test_parse_from_cmdline_allows_empty_arg_for_optional(self):
        class C(Corgy):
            x: Optional[int]

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["--x"])
        c = C.parse_from_cmdline(self.parser, add_help=False)
        self.assertEqual(c.x, None)

    def test_parse_from_cmdline_handles_positional_optional(self):
        class C(Corgy):
            x: Annotated[Optional[int], "x help", ["x"]]

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, [])
        c = C.parse_from_cmdline(self.parser, add_help=False)
        self.assertEqual(c.x, None)

    def test_parse_from_cmdline_allows_empty_arg_for_optional_collection(self):
        for _type in COLLECTION_TYPES:
            _core_types = [_type[int]]
            if _type not in (SequenceType, ListType, SetType):
                _core_types += [_type[int, ...], _type[int, int, int]]

            for _core_type in _core_types:
                with self.subTest(type=_core_type):

                    class C(Corgy):
                        x: Optional[_core_type]

                    self.setUp()
                    self.parser.parse_args = lambda: self.orig_parse_args(
                        self.parser, ["--x"]
                    )
                    c = C.parse_from_cmdline(self.parser, add_help=False)
                    self.assertEqual(c.x, None)

    def test_parse_from_cmdline_length_checks_optional_collection(self):
        def _raise_error(msg):
            raise ArgumentTypeError(None, msg)

        for _type in COLLECTION_TYPES:
            if _type in (SequenceType, ListType, SetType):
                continue

            class C(Corgy):
                x: Optional[_type[int, int, int]]

            for _args in [["1"], ["1", "2"], ["1", "2", "3", "4"]]:
                with self.subTest(type=_type, args=_args):
                    self.setUp()
                    self.parser.parse_args = lambda: self.orig_parse_args(
                        self.parser,
                        ["--x", *_args],  # pylint: disable=cell-var-from-loop
                    )
                    self.parser.error = _raise_error
                    with self.assertRaises(ArgumentTypeError):
                        C.parse_from_cmdline(self.parser, add_help=False)

    def test_parse_from_cmdline_raises_on_missing_required_attrs(self):
        class C(Corgy):
            x: Required[int]

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, [])

        def _raise_error(msg):
            raise ArgumentTypeError(None, msg)

        self.parser.error = _raise_error

        with self.assertRaises(ArgumentTypeError):
            C.parse_from_cmdline(self.parser, add_help=False)

    def test_parse_from_cmdline_handles_single_value_literal(self):
        class C(Corgy):
            x: Literal[42]

        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, ["--x"])
        c = C.parse_from_cmdline(self.parser)
        self.assertTrue(hasattr(c, "x"))

        self.setUp()
        self.parser.parse_args = lambda: self.orig_parse_args(self.parser, [])
        c = C.parse_from_cmdline(self.parser)
        self.assertFalse(hasattr(c, "x"))


@skipIf(tomli is None, "`tomli` package not found")
class TestCorgyTomlParsing(TestCase):
    def test_toml_file_parsed_to_corgy_object(self):
        class C(Corgy):
            x: int

        f = BytesIO(b"x = 1\n")
        c = C.parse_from_toml(f)
        self.assertEqual(c.x, 1)

    def test_toml_file_parsing_handles_colls(self):
        for _type in COLLECTION_TYPES:
            with self.subTest(type=_type):

                class C(Corgy):
                    x: _type[int]
                    y: _type[str]
                    z: Sequence[_type[int]]

                f = BytesIO(
                    b"x = [1, 2, 3]\ny = ['1', '2', '3']\nz = [ [1], [2, 3] ]\n"
                )
                c = C.parse_from_toml(f)
                if _type in (Tuple, TupleType):
                    self.assertTupleEqual(c.x, (1, 2, 3))
                    self.assertTupleEqual(c.y, ("1", "2", "3"))
                    self.assertListEqual(c.z, [(1,), (2, 3)])
                elif _type in (Set, SetType):
                    self.assertSetEqual(c.x, {1, 2, 3})
                    self.assertSetEqual(c.y, {"1", "2", "3"})
                    self.assertListEqual(c.z, [{1}, {2, 3}])
                else:
                    self.assertListEqual(c.x, [1, 2, 3])
                    self.assertListEqual(c.y, ["1", "2", "3"])
                    self.assertListEqual(c.z, [[1], [2, 3]])

    def test_toml_file_parsing_handles_defaults(self):
        class C(Corgy):
            x: int = 1
            y: str

        f = BytesIO(b"y = 'test'\n")
        c = C.parse_from_toml(f)
        self.assertEqual(c.x, 1)
        self.assertEqual(c.y, "test")

    def test_toml_file_parsing_handles_default_override(self):
        class C(Corgy):
            x: int = 1

        f = BytesIO(b"\n")
        c = C.parse_from_toml(f, defaults={"x": 2})
        self.assertEqual(c.x, 2)

    def test_toml_file_parsing_handles_groups(self):
        class G(Corgy):
            x: int
            y: str = "test"

        class C(Corgy):
            x: str
            g: G

        f = BytesIO(b"x = 'one'\n[g]\nx = 1\n")
        c = C.parse_from_toml(f)
        self.assertEqual(c.x, "one")
        self.assertTrue(hasattr(c, "g"))
        self.assertEqual(c.g.x, 1)
        self.assertEqual(c.g.y, "test")

    def test_toml_file_parsing_handles_subgroups(self):
        class C(Corgy):
            x: int

        class D(Corgy):
            x: str
            c: C

        class E(Corgy):
            x: int
            c: D
            d: D

        f = BytesIO(b"x = 1\n[c]\nx = '10'\n[d]\nx = 'one'\n[d.c]\nx = 100\n")
        e = E.parse_from_toml(f)
        self.assertEqual(e.x, 1)
        self.assertEqual(e.c.x, "10")
        self.assertEqual(e.d.x, "one")
        self.assertEqual(e.d.c.x, 100)

    def test_toml_file_parsing_handles_inherited_attributes(self):
        class G:
            x: int

        class C(Corgy, G):
            y: str

        class GCorgy(Corgy):
            x: int

        class CCorgy(GCorgy):
            y: str

        for cls in (C, CCorgy):
            f = BytesIO(b"x = 1\ny = 'test'\n")
            c = cls.parse_from_toml(f)
            self.assertEqual(c.x, 1)
            self.assertEqual(c.y, "test")

    def test_toml_file_parsing_handles_custom_parsers(self):
        class C(Corgy):
            x: int

            @corgyparser("x")
            @staticmethod
            def parsex(s: str):
                return int(s) + 1

        f = BytesIO(b"x = 1\n")
        c = C.parse_from_toml(f)
        self.assertEqual(c.x, 2)

    def test_toml_file_parsing_handles_custom_parsers_with_nargs(self):
        class C(Corgy):
            x: int

            @corgyparser("x", nargs=3)
            @staticmethod
            def parsex(s):
                return sum(map(int, s))

        f = BytesIO(b"x = [1, 2, 3]\n")
        c = C.parse_from_toml(f)
        self.assertEqual(c.x, 6)


class TestCorgyEquality(TestCase):
    def test_corgy_instance_is_equal_to_itself(self):
        class A(Corgy):
            x: int

        a = A(x=1)
        self.assertEqual(a, a)

    def test_corgy_instances_are_equal_when_all_attrs_same(self):
        class A(Corgy):
            x: int

        a1 = A(x=1)
        a2 = A(x=1)
        self.assertEqual(a1, a2)

    def test_corgy_instances_are_equal_when_unset_attrs_match(self):
        class A(Corgy):
            x: int
            y: str

        a1 = A(x=1)
        a2 = A(x=1)
        self.assertEqual(a1, a2)

    def test_corgy_instances_are_unequal_when_unset_attrs_dont_match(self):
        class A(Corgy):
            x: int
            y: str

        a1 = A(x=1)
        a2 = A(x=1, y="2")
        self.assertNotEqual(a1, a2)

    def test_corgy_instances_are_equal_when_default_val_overwritten(self):
        class A(Corgy):
            x: int = 1

        a1 = A()
        a2 = A()
        a2.x = 1
        self.assertEqual(a1, a2)

    def test_corgy_instance_equality_handles_groups(self):
        class A(Corgy):
            x: int

        class B(Corgy):
            x: str
            a: A

        b1 = B(x="1", a=A(x=1))
        b2 = B(x="1", a=A(x=1))
        b3 = B(x="1", a=A())
        self.assertEqual(b1, b2)
        self.assertNotEqual(b2, b3)

    def test_corgy_instance_not_equal_to_sub_class(self):
        class A(Corgy):
            x: int

        class B(A):
            ...

        a = A(x=1)
        b = B(x=1)
        self.assertNotEqual(a, b)

    def test_corgy_instance_not_equal_to_non_corgy_type(self):
        class A(Corgy):
            x: int

        class B:
            ...

        a = A(x=1)
        b = B()
        b.x = 1
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, 1)

    def test_corgy_instance_equality_ignores_extra_attrs(self):
        class A(Corgy, corgy_make_slots=False):
            x: int

        a1 = A(x=1)
        a1.y = "1"
        a2 = A(x=1)
        a2.y = "2"
        self.assertEqual(a1, a2)

    def test_corgy_instance_equality_handles_inherited_attrs(self):
        class A:
            x: int

        class B(Corgy, A):
            y: str

        b1 = B(x=1, y="2")
        b2 = B(x=1, y="2")
        self.assertEqual(b1, b2)

        class C(Corgy, A, corgy_track_bases=False):
            y: str

        c1 = C(y="2")
        c1.x = 1
        c2 = C(y="2")
        c2.x = 2
        self.assertEqual(c1, c2)


class TestCorgyFreeze(TestCase):
    def test_corgy_attrs_cannot_be_set_after_freeze(self):
        class A(Corgy):
            x: int

        a = A()
        a.freeze()
        with self.assertRaises(TypeError):
            a.x = 2

        a = A(x=1)
        a.freeze()
        with self.assertRaises(TypeError):
            a.x = 2

    def test_corgy_attrs_cannot_be_deleted_after_freeze(self):
        class A(Corgy):
            x: int

        a = A(x=1)
        a.freeze()
        with self.assertRaises(TypeError):
            del a.x

    def test_double_freeze_is_noop(self):
        class A(Corgy):
            x: int

        a = A(x=1)
        a.freeze()
        with self.assertRaises(TypeError):
            a.x = 2
        a.freeze()
        with self.assertRaises(TypeError):
            a.x = 2

    def test_setting_corgy_freeze_after_init_freezes_instance(self):
        class A(Corgy, corgy_freeze_after_init=True):
            x: int

        a = A(x=1)
        with self.assertRaises(TypeError):
            a.x = 2

        a = A(x=1)
        a.freeze()
        with self.assertRaises(TypeError):
            a.x = 2
