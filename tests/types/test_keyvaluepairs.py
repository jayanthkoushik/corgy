import pickle
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from corgy.types import KeyValuePairs

from ._pklclasses import PklTestB, PklTestC


class TestKeyValuePairs(TestCase):
    def test_key_value_pairs_init_returns_unique_class(self):
        type_ = KeyValuePairs[str, int]
        self.assertIsNot(type_, KeyValuePairs)

    def test_key_value_pairs_init_caches_calls(self):
        type_ = KeyValuePairs[str, int]
        self.assertIs(type_, KeyValuePairs[str, int])
        self.assertIsNot(type_, KeyValuePairs[int, str])

    def test_key_value_pairs_init_handles_type_being_unhashable(self):
        class M(type):
            __hash__ = None

        class A(metaclass=M):
            ...

        type_ = KeyValuePairs[A, str]
        self.assertIsNot(type_, KeyValuePairs[A, str])
        type_ = KeyValuePairs[str, A]
        self.assertIsNot(type_, KeyValuePairs[str, A])

    def test_key_value_pairs_raises_if_re_subscripted(self):
        type_ = KeyValuePairs[str, int]
        with self.assertRaises(TypeError):
            type_[str, int]  # type: ignore # pylint: disable=pointless-statement

    def test_key_value_pairs_returns_dict_like(self):
        type_ = KeyValuePairs[str, str]
        dic = type_("foo=1,bar=2")
        self.assertDictEqual(dic, {"foo": "1", "bar": "2"})

    def test_key_value_pairs_allows_call_without_init(self):
        dic = KeyValuePairs("foo=1,bar=2")
        self.assertDictEqual(dic, {"foo": "1", "bar": "2"})

    def test_key_value_pairs_handles_empty_string(self):
        self.assertDictEqual(KeyValuePairs(""), {})

    def test_key_value_pairs_raises_if_any_item_not_correct_format(self):
        with self.assertRaises(ValueError):
            KeyValuePairs("foo=1,bar2")

    def test_key_value_pairs_handles_multiple_separators_in_item(self):
        dic = KeyValuePairs("foo==1,bar=2=3")
        self.assertDictEqual(dic, {"foo": "=1", "bar": "2=3"})

    def test_key_value_pairs_handles_type_casting(self):
        type_ = KeyValuePairs[int, float]
        dic = type_("1=2.0,3=4.0")
        self.assertDictEqual(dic, {1: float("2.0"), 3: float("4.0")})

    def test_key_value_pairs_raises_if_type_casting_fails(self):
        type_ = KeyValuePairs[int, int]
        with self.assertRaises(ValueError):
            type_("foo=1")
        with self.assertRaises(ValueError):
            type_("1=foo")

    def test_key_value_pairs_handles_type_casting_with_custom_type(self):
        class A:
            def __init__(self, x):
                self.x = x

            def __eq__(self, other):
                return isinstance(other, A) and self.x == other.x

        type_ = KeyValuePairs[str, A]
        dic = type_("foo=1,bar=2")
        self.assertDictEqual(dic, {"foo": A("1"), "bar": A("2")})

    def test_key_value_pairs_metavar(self):
        self.assertEqual(KeyValuePairs.__metavar__, "key=val,...")
        self.assertEqual(KeyValuePairs[str, int].__metavar__, "key=val,...")

    def test_key_value_pairs_handles_custom_sequence_separator(self):
        type_ = KeyValuePairs[str, str]
        with patch.object(type_, "sequence_separator", ";"):
            dic = type_("foo=1;bar=2")
            self.assertDictEqual(dic, {"foo": "1", "bar": "2"})
            self.assertEqual(type_.__metavar__, "key=val;...")

    def test_key_value_pairs_handles_custom_item_separator(self):
        type_ = KeyValuePairs[str, str]
        with patch.object(type_, "item_separator", ":"):
            dic = type_("foo:1,bar:2")
            self.assertDictEqual(dic, {"foo": "1", "bar": "2"})
            self.assertEqual(type_.__metavar__, "key:val,...")

    def test_key_value_pairs_subtype_not_affected_by_changes_to_base_type(self):
        type_ = KeyValuePairs[str, int]
        with patch.multiple(KeyValuePairs, sequence_separator=";", item_separator=":"):
            self.assertEqual(type_.sequence_separator, ",")
            self.assertEqual(type_.item_separator, "=")

    def test_key_value_pairs_repr_str(self):
        type_ = KeyValuePairs[str, int]
        dic = type_("foo=1,bar=2")
        self.assertEqual(repr(dic), "KeyValuePairs[str,int]('foo=1,bar=2')")
        self.assertEqual(str(dic), "{'foo': 1, 'bar': 2}")

    def test_key_value_pairs_repr_str_with_custom_separators(self):
        with patch.multiple(KeyValuePairs, sequence_separator=";", item_separator=":"):
            dic = KeyValuePairs("foo:1;bar:2")
            self.assertEqual(repr(dic), "KeyValuePairs('foo:1;bar:2')")
            self.assertEqual(str(dic), "{'foo': '1', 'bar': '2'}")

    def test_key_value_pairs_accepts_dict(self):
        dic = KeyValuePairs[str, int]({"foo": 1, "bar": 2})
        self.assertDictEqual(dic, {"foo": 1, "bar": 2})
        self.assertEqual(repr(dic), "KeyValuePairs[str,int]({'foo': 1, 'bar': 2})")

    def test_key_value_pairs_pickleable(self):
        with TemporaryDirectory() as _tmpdir:
            _pkl_path = Path(_tmpdir) / "tmp.pkl"

            _KVT = KeyValuePairs[PklTestB, PklTestC]
            _b1, _b2 = PklTestB(1), PklTestB(2)
            _c1, _c2 = PklTestC(1), PklTestC(2)
            _kv = _KVT({_b1: _c1, _b2: _c2})

            with _pkl_path.open("wb") as _f:
                pickle.dump(_kv, _f)

            with _pkl_path.open("rb") as _f:
                _pkv = pickle.load(_f)

            self.assertDictEqual(_kv, _pkv)
