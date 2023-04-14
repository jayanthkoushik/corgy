# corgy package

Corgy package for elegant data classes.


### _class_ corgy.Corgy(\*\*args)
Base class for collections of attributes.

To use, subclass `Corgy`, and declare attributes using type annotations:

```python
>>> from corgy import Corgy

>>> class A(Corgy):
...     x: int
...     y: float
```

At runtime, class `A` will have `x`, and `y` as properties, so that the class can be
used similar to Python dataclasses:

```python
>>> a = A()
>>> a.x = 1
>>> a.x
1

>>> a.y
Traceback (most recent call last):
   ...
AttributeError: no value available for attribute `y`

>>> a.y = a.x + 1.1
>>> a.y
2.1

>>> del a.x  # unset x
>>> a.x
Traceback (most recent call last):
   ...
AttributeError: no value available for attribute `x`
```

Note that the class’s `__init__` method only accepts keyword arguments, and ignores
arguments without a corresponding attribute. The following are all valid:

```python
>>> A(x=1, y=2.1)
A(x=1, y=2.1)

>>> A(x=1, z=3)  # y is not set, and z is ignored
A(x=1)

>>> A(**{"x": 1, "y": 2.1, "z": 3})
A(x=1, y=2.1)
```

Attribute values are type-checked, and `ValueError` is raised on type mismatch:

```python
>>> a = A(x="1")
Traceback (most recent call last):
    ...
ValueError: invalid value for type '<class 'int'>': '1'

>>> a = A()
>>> a.x = "1"
Traceback (most recent call last):
    ...
ValueError: invalid value for type '<class 'int'>': '1'

>>> class A(Corgy):
...     x: int = "1"
Traceback (most recent call last):
    ...
ValueError: default value type mismatch for 'x'
```

Any type which supports type checking with `isinstance` can be used as an
attribute type (along with some special type annotations that are discussed below).
This includes other corgy classes:

```python
>>> class A(Corgy):
...     x: int
...     y: float

>>> class B(Corgy):
...     x: int
...     a: A

>>> b = B(x=1)
>>> b.a = A()
>>> b.a.x = 10
>>> b
B(x=1, a=A(x=10))
```

`Corgy` classes have their `__slots__` set to the annotated attributes. So, if you
want to use additional attributes not tracked by `Corgy`, define them (and only
them) in `__slots__`:

```python
>>> class A(Corgy):
...     __slots__ = ("x",)
...     y: int

>>> a = A()
>>> a.y = 1  # `Corgy` attribute
>>> a.x = 2  # custom attribute
>>> a
A(y=1)
```

To allow arbitrary instance attributes, add `__dict__` to `__slots__`. Names added
through custom `__slots__` are not processed by `Corgy`. Alternatively, to disable
setting `__slots__` completely, set `corgy_make_slots` to `False` in the class
definition:

```python
>>> class A(Corgy, corgy_make_slots=False):
...     y: int

>>> a = A()
>>> a.y = 1  # `Corgy` attribute
>>> a.x = 2  # custom attribute
>>> a
A(y=1)
```

Names marked with the `ClassVar` type will be added as class variables, and will
not be available as `Corgy` attributes:

```python
>>> from typing import ClassVar

>>> class A(Corgy):
...     x: ClassVar[int] = 3

>>> A.x
3
>>> A.x = 4
>>> A.x
4
>>> a = A()
>>> a.x
4
>>> a.x = 5
Traceback (most recent call last):
    ...
AttributeError: 'A' object attribute 'x' is read-only
```

Also note that class variables need to be assigned to a value during definition, and
this value will not be type checked by `Corgy`.

Inheritance works as expected, whether base classes are themselves `Corgy` classes
or not, with sub-classes inheriting the attributes of the base class, and overriding
any redefined attributes:

```python
>>> class A:
...     x: int

>>> class B(Corgy, A):
...     y: float = 1.0
...     z: str

>>> class C(B):
...     y: float = 2.0
...     z: str
...     w: float

>>> c = C()
>>> print(c)
C(x=<unset>, y=2.0, z=<unset>, w=<unset>)
```

Tracking of base class attributes can be disabled by setting `corgy_track_bases` to
`False` in the class definition. Properties will still be inherited following
standard inheritance rules, but `Corgy` will ignore them:

```python
>>> class A:
...     x: int

>>> class B(Corgy, A, corgy_track_bases=False):
...     y: float = 1.0
...     z: str

>>> b = B()
>>> print(b)
B(y=1.0, z=<unset>)
```

`Corgy` instances can be frozen (preventing any further changes) using the `freeze`
method. This method can be called automatically after `__init__` by by setting
`corgy_freeze_after_init` to `True` in the class definition:

```python
>>> class A(Corgy, corgy_freeze_after_init=True):
...    x: int

>>> a = A(x=1)
>>> a.x = 2
Traceback (most recent call last):
    ...
TypeError: cannot set `x`: object is frozen
```

`Corgy` recognizes a number of special annotations, which are used to control how
attribute values are processed.

**NOTE**: If any of the following annotations are unavailable in the Python version being
used, you can import them from `typing_extensions` (which is available on PyPI).

*Annotations*
`typing.Annotated` can be used to add additional metadata to attributes, akin to
doc strings. It is primarily used to control how attributes are added to
`ArgumentParser` instances. `typing.Annotated` is stripped on class creation,
leaving only the base type:

```python
>>> import sys
>>> if sys.version_info >= (3, 9):
...     from typing import Annotated, Literal
... else:
...     from typing_extensions import Annotated, Literal

>>> class A(Corgy):
...     x: Annotated[int, "this is x"]

>>> A.attrs()
{'x': <class 'int'>}
```

`Annotated` should always be the outermost type annotation for an attribute.
Refer to the docs for `Corgy.add_args_to_parser` for details on usage.

*Required/NotRequired*
By default, `Corgy` attributes are not required, and can be unset. This can be
changed by setting `corgy_required_by_default` to `True` in the class definition:

```python
>>> class A(Corgy, corgy_required_by_default=True):
...     x: int

>>> A()
Traceback (most recent call last):
    ...
ValueError: missing required attribute: `x`
>>> a = A(x=1)
>>> del a.x
Traceback (most recent call last):
    ...
TypeError: attribute `x` cannot be unset
```

Attributes can also explicitly be marked as required/not-required using
`corgy.Required` and `corgy.NotRequired` annotations:

```python
>>> from corgy import Required, NotRequired

>>> class A(Corgy):
...     x: Required[int]
...     y: NotRequired[int]
...     z: int  # not required by default

>>> a = A(x=1)
>>> print(a)
A(x=1, y=<unset>, z=<unset>)

>>> class B(Corgy, corgy_required_by_default=True):
...     x: Required[int]
...     y: NotRequired[int]
...     z: int

>>> b = B(x=1, z=2)
>>> print(b)
B(x=1, y=<unset>, z=2)
```

*Optional*
Annotating an attribute with `typing.Optional` allows it to be `None`:

```python
>>> from typing import Optional

>>> class A(Corgy):
...     x: Optional[int]

>>> a = A()
>>> a.x = None
```

In Python >= 3.10, instead of using `typing.Annotated`, `| None` can be used, i.e.,
`x: int | None` for example.

Note that `Optional` is not the same as `NotRequired`. `Optional` allows an
attribute to be `None`, while `NotRequired` allows an attribute to be unset.
A `Required` `Optional` attribute will need a value (which can be `None`):

```python
>>> class A(Corgy):
...     x: Required[Optional[int]]

>>> A()
Traceback (most recent call last):
    ...
ValueError: missing required attribute: `x`
>>> a = A(x=None)
>>> print(a)
A(x=None)
```

*Collections*
Several collection types can be used to annotate attributes, which will restrict the
type of accepted values. Values in the collection will be checked to ensure that
they match the annotated collection types. The following collection types are
supported:


1. `collections.abc.Sequence` (`typing.Sequence` on Python < 3.9)


2. `tuple` (`typing.Tuple` on Python < 3.9)


3. `list` (`typing.List` on Python < 3.9)


4. `set` (`typing.Set` on Python < 3.9)

There are a few different ways to use these types, each resulting in different
validation conditions. The simplest case is a plain (possibly empty) collection of a
single type:

```python
>>> from typing import List, Sequence, Set, Tuple

>>> class A(Corgy):
...     x: Sequence[int]
...     y: Tuple[str]
...     z: Set[float]
...     w: List[int]

>>> a = A()
>>> a.x = [1, 2]
>>> a.y = ("1", "2")
>>> a.z = {1.0, 2.0}
>>> a.w = [1, 2]
>>> a
A(x=[1, 2], y=('1', '2'), z={1.0, 2.0}, w=[1, 2])

>>> a.x = [1, "2"]
Traceback (most recent call last):
    ...
ValueError: invalid value for type '<class 'int'>': '2'

>>> a.x = (1, 2)      # `Sequence` accepts any sequence type

>>> a.y = ["1", "2"]  # `Tuple` only accepts tuples
Traceback (most recent call last):
    ...
ValueError: invalid value for type 'typing.Tuple[str]': ['1', '2']
```

The collection length can be controlled by the arguments of the type annotation.
Note, however, that `typing.Sequence/typing.List/typing.Set` do not
accept multiple arguments, and so, cannot be used if collection length has to be
specified. On Python < 3.9, only `typing.Tuple` can be used for controlling
collection lengths.

To specify that a collection must be non-empty, use ellipsis (`...`) as the second
argument of the type:

```python
>>> class A(Corgy):
...     x: Tuple[int, ...]

>>> a = A()
>>> a.x = tuple()
Traceback (most recent call last):
    ...
ValueError: expected non-empty collection for type 'typing.Tuple[int, ...]'
```

Collections can also be restricted to be of a fixed length:

```python
>>> class A(Corgy):
...     x: Tuple[int, str]
...     y: Tuple[int, int, int]

>>> a = A()
>>> a.x = (1, 1)
Traceback (most recent call last):
    ...
ValueError: invalid value for type '<class 'str'>': 1

>>> a.y = (1, 1)
Traceback (most recent call last):
    ...
ValueError: invalid value for type 'typing.Tuple[int, int, int]': (1, 1):
expected exactly '3' elements
```

*Literals*
`typing.Literal` can be used to specify that an attribute takes one of a fixed set
of values:

```python
>>> class A(Corgy):
...     x: Literal[0, 1, "2"]

>>> a = A()
>>> a.x = 0
>>> a.x = "2"
>>> a.x = "1"
Traceback (most recent call last):
    ...
ValueError: invalid value for type 'typing.Literal[0, 1, '2']': '1'
```

Type annotations can be nested; for instance,
`Sequence[Literal[0, 1, 2], Literal[0, 1, 2]]` represents a sequence of length 2,
where each element is either 0, 1, or 2.

A fixed set of attribute values can also be specified by adding a `__choices__`
attribute to the argument type, containing a collection of choices:

```python
>>> class T(int):
...     __choices__ = (1, 2)

>>> class A(Corgy):
...     x: T

>>> a = A()
>>> a.x = 1
>>> a.x = 3
Traceback (most recent call last):
    ...
ValueError: invalid value for type '<class 'T'>': 3:
expected one of: (1, 2)
```

Note that choices specified in this way are not type-checked to ensure that they
match the argument type; in the above example, `__choices__` could be set to
`(1, "2")`.


#### _classmethod_ add_args_to_parser(parser, name_prefix='', flatten_subgrps=False, defaults=None)
Add the class’ `Corgy` attributes to the given parser.


* **Parameters**


    * **parser** – Argument parser/group to which the attributes will be added.


    * **name_prefix** – Prefix for argument names. Arguments will be named
    `--<name-prefix>:<attr-name>`. If custom flags are present,
    `--<name-prefix>:<flag>` will be used instead (one for each flag).


    * **flatten_subgrps** – Whether to add sub-groups to the main parser instead of
    creating argument groups. Note: sub-sub-groups are always added with
    this argument set to `True`, since `argparse` in unable to properly
    display nested group arguments.


    * **defaults** – Optional mapping with default values for arguments. Any value
    specified here will override default values specified in the class.
    Values for groups can be specified either as `Corgy` instances, or as
    individual values using the same syntax as for `Corgy.from_dict`.


Type annotations control how attributes are added to the parser. A number of
special annotations are parsed and stripped from attribute types to determine
the parameters for calling `ArgumentParser.add_argument`. These special
annotations are described below.

*Annotated*
`typing.Annotated` can be used to add a help message for the argument:

```python
>>> import argparse
>>> from argparse import ArgumentParser
>>> from corgy import CorgyHelpFormatter

>>> class A(Corgy):
...     x: Annotated[int, "help for x"]

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )

>>> A.add_args_to_parser(parser)
>>> parser.print_help()
options:
  --x int  help for x (optional)
```

This annotation can also be used to modify the parser flags for the argument. By
default, the attribute name is used, prefixed with `--`, and with `_` replaced
by `-`. If the custom flag does not have a leading `-`, a positional argument
will be created:

```python
>>> class A(Corgy):
...     x: Annotated[int, "help for x", ["-x", "--ex"]]
...     y: Annotated[int, "help for y", ["y"]]

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )

>>> A.add_args_to_parser(parser)
>>> parser.print_help()
positional arguments:
  y int        help for y

options:
  -x/--ex int  help for x (optional)
```

`Annotated` can accept multiple arguments, but only the first three are used
by `Corgy`. The first argument is the attribute type, the second is the help
message (which must be a string), and the third is a sequence of flags.

*Required/NotRequired*
Every corgy attribute is either required or not required. The default status
depends on the class parameter `corgy_required_by_default` (`False` by default).
Attributes can also be explicitly marked as required or not required, and will
control whether the argument will be added with `required=True`:

```python
>>> from corgy import Required, NotRequired

>>> class A(Corgy):
...     x: Required[int]
...     y: NotRequired[int]
...     z: int

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )

>>> A.add_args_to_parser(parser)
>>> parser.print_help()
options:
  --x int  (required)
  --y int  (optional)
  --z int  (optional)
```

Attributes which are not required, and don’t have a default value are added
with `default=argparse.SUPPRESS`, and so will not be in the parsed namespace:

```python
>>> parser.parse_args(["--x", "1", "--y", "2"])
Namespace(x=1, y=2)
```

*Optional*
Attributes marked with `typing.Optional` are allowed to be `None`. The
arguments for these attributes can be passed with no values (i.e. `--x`
instead of `--x=1` or `--x 1`) to indicate that the value should be `None`.

Note: Attributes with default values are also “optional” in the sense that
they can be omitted from the command line. However, they are not the same as
attributes marked with `Optional`, since the former are not allowed to be
`None`. Furthermore, `Required` `Optional` attributes without default values
_will_ need to be passed on the command line (possibly with no values).

```python
>>> class A(Corgy):
...     x: Required[Optional[int]]
```

```python
>>> parser = ArgumentParser()
>>> A.add_args_to_parser(parser)
>>> parser.parse_args(["--x"])
Namespace(x=None)
```

*Boolean*
`bool` types (when not in a collection) are converted to a pair of options:

```python
>>> class A(Corgy):
...     arg: bool

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )

>>> A.add_args_to_parser(parser)
>>> parser.print_help()
options:
  --arg/--no-arg
```

*Collection*
Collection types are added to the parser by setting `nargs`. The value for
`nargs` is determined by the collection type. Plain collections, such as
`Sequence[int]`, will be added with `nargs=\*`; Non-empty collections, such as
`Sequence[int, ...]`, will be added with `nargs=+`; Finally, fixed-length
collections, such as `Sequence[int, int, int]`, will be added with `nargs` set
to the length of the collection.

In all cases, collection types can only be added to a parser if they are single
type. Heterogenous collections, such as `Sequence[int, str]` cannot be added,
and will raise `ValueError`. Untyped collections (e.g., `x: Sequence`), also
cannot be added.

Arguments for optional collections will also accept no values to indicate
`None`. Due to this, it is not possible to parse an empty collection for
an optional collection argument:

```python
>>> class A(Corgy):
...     x: Optional[Sequence[int]]
...     y: Sequence[int]

>>> parser = ArgumentParser()
>>> A.add_args_to_parser(parser)
>>> parser.parse_args(["--x", "--y"])
Namespace(x=None, y=[])
```

*Literal*
For `Literal` types, the provided values are passed to the `choices` argument
of `ArgumentParser.add_argument`. All values must be of the same type, which
will be inferred from the type of the first value. If the first value has a
`__bases__` attribute, the type will be inferred as the first base type, and
all other choices must be subclasses of that type:

```python
>>> class T: ...
>>> class T1(T): ...
>>> class T2(T): ...

>>> class A(Corgy):
...     x: Literal[T1, T2]

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )

>>> A.add_args_to_parser(parser)
>>> parser.print_help()
options:
  --x T  ({T1/T2} optional)
```

For types which specify choices by defining `__choices__`, the values are
passed to the `choices` argument as with `Literal`, but no type inference is
performed, and the base attribute type will be used as the argument type.

**Single-value Literals**
A special case for `Literal` types is when there is only one choice. In this
case, the argument is added as a `store_const` action, with the value as the
`const` argument. A further special case is when the choice is `True/False`,
in which case the action is `store_true`/`store_false` respectively:

```python
>>> class A(Corgy):
...     x: Literal[True]
...     y: Literal[False]
...     z: Literal[42]

>>> parser = ArgumentParser()
>>> A.add_args_to_parser(parser)
>>> parser.parse_args(["--x"])  # Note that `y` and `z` are absent
Namespace(x=True)
>>> parser.parse_args(["--y"])
Namespace(y=False)
>>> parser.parse_args(["--z"])
Namespace(z=42)
```

*Corgy*
Attributes which are themselves `Corgy` types are treated as argument groups.
Group arguments are added to the command line parser with the group attribute
name prefixed. Note that groups will ignore any custom flags when computing the
prefix; elements within the group will use custom flags, but because they are
prefixed with `--`, they will not be positional.

Example:

```python
>>> class G(Corgy):
...     x: int = 0
...     y: float

>>> class A(Corgy):
...     x: int
...     g: G

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )

>>> A.add_args_to_parser(parser)
>>> parser.print_help()
options:
  --x int      (optional)

g:
  --g:x int    (default: 0)
  --g:y float  (optional)
```

**Custom parsers**

Attributes for which a custom parser is defined using `@corgyparser` will
be added with a custom action that will call the parser. Refer to the
documentation for `corgyparser` for details.

**Metavar**

This function will not explicitly pass a value for the `metavar` argument of
`ArgumentParser.add_argument`, unless an attribute’s type defines `__metavar__`,
in which case, it will be passed as is. To change the metavar for attributes
with custom parsers, set the `metavar` argument of `corgyparser`.


#### _classmethod_ attrs()
Return a dictionary mapping attributes of the class to their types.

Example:

```python
>>> class A(Corgy):
...     x: Annotated[int, "x"]
...     y: Sequence[str]

>>> A.attrs()
{'x': <class 'int'>, 'y': typing.Sequence[str]}
```


#### as_dict(recursive=True, flatten=False)
Return the object as a dictionary.

The returned dictionary maps attribute names to their values. Unset attributes
are omitted, unless they have default values.


* **Parameters**


    * **recursive** – whether to recursively call `as_dict` on attributes which are
    `Corgy` instances. Otherwise, they are returned as is.


    * **flatten** – whether to flatten group arguments into `:` separated strings.
    Only takes effect if `recursive` is `True`.


Examples:

```python
>>> class G(Corgy):
...     x: int

>>> g = G(x=1)
>>> g.as_dict()
{'x': 1}

>>> class A(Corgy):
...     x: str
...     g: G

>>> a = A(x="one", g=g)
>>> a.as_dict(recursive=False)
{'x': 'one', 'g': G(x=1)}
>>> a.as_dict()
{'x': 'one', 'g': {'x': 1}}
>>> a.as_dict(flatten=True)
{'x': 'one', 'g:x': 1}
```


#### _classmethod_ from_dict(d, try_cast=False)
Return a new instance of the class using a dictionary.

This is roughly equivalent to `cls(\*\*d)`, with the main exception being that
groups can be specified as dictionaries themselves, and will be processed
recursively.


* **Parameters**


    * **d** – Dictionary to create the instance from.


    * **try_cast** – Whether to try and cast values which don’t match attribute types.


Example:

```python
>>> class G(Corgy):
...     x: int

>>> class A(Corgy):
...     x: str
...     g: G

>>> A.from_dict({"x": "one", "g": G(x=1)})
A(x='one', g=G(x=1))
>>> A.from_dict({"x": "one", "g": {"x": 1}})
A(x='one', g=G(x=1))
>>> A.from_dict({"x": "one", "g": {"x": "1"}}, try_cast=True)
A(x='one', g=G(x=1))
```

Group attributes can also be passed directly in the dictionary by prefixing
their names with the group name and a colon:

```python
>>> A.from_dict({"x": "one", "g:x": 1})
A(x='one', g=G(x=1))

>>> class B(Corgy):
...     x: float
...     a: A

>>> B.from_dict({"x": 1.1, "a:x": "one", "a:g:x": 1})
B(x=1.1, a=A(x='one', g=G(x=1)))
```


#### load_dict(d, try_cast=False, strict=False)
Load a dictionary into an instance of the class.

Previous attributes are overwritten. Sub-dictionaries will be parsed
recursively if the corresponding attribute already exists, else will be parsed
using `from_dict`. As with `from_dict`, items in the dictionary without
corresponding attributes are ignored.


* **Parameters**


    * **d** – Dictionary to load.


    * **try_cast** – Whether to try and cast values which don’t match attribute types.


    * **strict** – If `True`, attributes with existing values that are not in the
    dictionary will be unset.


Example:

```python
>>> class A(Corgy):
...     x: int
...     y: str
>>> a = A(x=1)
>>> _i = id(a)
>>> a.load_dict({"y": "two"})
>>> a
A(x=1, y='two')
>>> _i == id(a)
True
>>> a.load_dict({"y": "three"}, strict=True)
>>> a
A(y='three')
>>> _i == id(a)
True
```


#### _classmethod_ parse_from_cmdline(parser=None, defaults=None, \*\*parser_args)
Return an instance of the class parsed from command line arguments.


* **Parameters**


    * **parser** – An instance of `argparse.ArgumentParser` or `None`. If `None`, a new
    instance is created.


    * **defaults** – A dictionary of default values for the attributes, passed to
    `add_args_to_parser`. Refer to the docs for `add_args_to_parser` for
    more details.


    * **parser_args** – Arguments to be passed to `argparse.ArgumentParser()`. Ignored
    if `parser` is not None.



* **Raises**

    **ArgumentTypeError** – Error parsing command line arguments.



#### _classmethod_ parse_from_toml(toml_file, defaults=None)
Parse an object of the class from a toml file.


* **Parameters**


    * **toml_file** – A file-like object containing the class attributes in toml.


    * **defaults** – A dictionary of default values, overriding any values specified
    in the class.



* **Raises**

    **TOMLDecodeError** – Error parsing the toml file.


Example:

```python
>>> class G(Corgy):
...     x: int
...     y: Sequence[int]

>>> class A(Corgy):
...     x: str
...     g: G

>>> from io import BytesIO
>>> f = BytesIO(b'''
...     x = 'one'
...     [g]
...     x = 1
...     y = [1, 2, 3]
... ''')

>>> A.parse_from_toml(f)
A(x='one', g=G(x=1, y=[1, 2, 3]))
```


#### freeze()
Freeze the object, preventing any further changes to attributes.

Example:

```python
>>> class A(Corgy):
...     x: int
...     y: int

>>> a = A(x=1, y=2)
>>> a.x = 2
>>> a.freeze()
>>> a.x = 3
Traceback (most recent call last):
    ...
TypeError: cannot set `x`: object is frozen
>>> del a.y
Traceback (most recent call last):
    ...
TypeError: cannot delete `y`: object is frozen
```


### corgy.corgyparser(\*var_names, metavar=None, nargs=None)
Decorate a function as a custom parser for one or more attributes.

To use a custom function for parsing a `Corgy` attribute, use this decorator.
Parsing functions must be static, and should only accept a single argument.
Decorating the function with `@staticmethod` is optional, but prevents type errors.
`@corgyparser` must be the final decorator in the decorator chain.


* **Parameters**


    * **var_names** – The attributes associated with the decorated parser.


    * **metavar** – Keyword only argument to set the metavar when adding the associated
    attribute(s) to an `ArgumentParser` instance.


    * **nargs** – Keyword only argument to set the number of arguments to be used for the
    associated attribute(s). Must be `None`, `'\*'`, `'+'`, or a positive number.
    This value is passed as the `nargs` argument to
    `ArgumentParser.add_argument`, and controls the number of arguments that
    will be read from the command line, and passed to the parsing function.
    For all values other than `None`, the parsing function will receive a list
    of strings.


Example:

```python
>>> import argparse
>>> from argparse import ArgumentParser
>>> from typing import Tuple
>>> from corgy import Corgy, CorgyHelpFormatter, corgyparser

>>> class A(Corgy):
...     time: Tuple[int, int, int]
...     @corgyparser("time", metavar="int:int:int")
...     @staticmethod
...     def parse_time(s):
...         return tuple(map(int, s.split(":")))

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )

>>> A.add_args_to_parser(parser)
>>> parser.parse_args(["--time", "1:2:3"])
Namespace(time=(1, 2, 3))
```

Multiple arguments can be passed to the decorator, and will all be associated with
the same parser:

```python
>>> class A(Corgy):
...     x: int
...     y: int
...     @corgyparser("x", "y")
...     @staticmethod
...     def parse_x_y(s):
...         return int(s)
```

The `@corgyparser` decorator can also be chained to use the same parser for multiple
arguments:

```python
>>> class A(Corgy):
...     x: int
...     y: int
...     @corgyparser("x")
...     @corgyparser("y")
...     @staticmethod
...     def parse_x_y(s):
...         return int(s)
```

Note: when chaining, the outer-most non-`None` value of `metavar` will be used.

Custom parsers can control the number of arguments they receive, independent of the
argument type:

```python
>>> class A(Corgy):
...     x: int
...     @corgyparser("x", nargs=3)
...     @staticmethod
...     def parse_x(s):
...         # `s` will be a list of 3 strings.
...         return sum(map(int, s))

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )

>>> A.add_args_to_parser(parser)
>>> parser.parse_args(["--x", "1", "2", "3"])
Namespace(x=6)
```

When chaining, `nargs` must be the same for all decorators, otherwise `TypeError` is
raised.


### _class_ corgy.CorgyHelpFormatter(prog)
Formatter class for `argparse` with a cleaner layout, and support for colors.

`Corgy.parse_from_cmdline` uses this formatter by default, unless a different
`formatter_class` argument is provided. `CorgyHelpFormatter` can also be used
independently of `Corgy`. Simply pass it as the `formatter_class` argument to
`argparse.ArgumentParser()`:

```python
>>> import argparse
>>> from argparse import ArgumentParser
>>> from corgy import CorgyHelpFormatter

>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     usage=argparse.SUPPRESS,
... )
>>> _ = parser.add_argument("--x", type=int, required=True)
>>> _ = parser.add_argument("--y", type=str, nargs="*", required=True)
>>> parser.print_help()
options:
  -h/--help      show this help message and exit
  --x int        (required)
  --y [str ...]  (required)
```

To configure `CorgyHelpFormatter`, you can set a number of attributes on the class.
Note that you do not need to create an instance of the class; that is done by the
parser itself. The following public attributes are available:


* `enable_colors`: If `None` (the default), colors are enabled if the `crayons`
package is available, and the output is a tty. To explicitly enable or disable
colors, set to `True` or `False`.


* `color_<choices/keywords/metavars/defaults/options>`: These attributes control
the colors used for various parts of the output (see below for reference).
Available colors are `red`, `green`, `yellow`, `blue`, `black`, `magenta`, `cyan`,
and `white`. Specifying the name in all caps will make the color bold. You can
also use the special value `BOLD` to make the output bold without changing the
color. The default value are `blue` for choices, `green` for keywords, `RED` for
metavars, `YELLOW` for defaults, and `BOLD` for options. Format:

```text
    -a/--arg str       help for arg ({'a'/'b'/'c'} default: 'a')
      |      |                          |            |      |
    options  metavars                 choices      keywords defaults
```


* `output_width`: The number of columns used for the output. If `None` (the
default), the current terminal width is used.


* `max_help_position`: How far to the right (from the start), the help string can
start from. If `None`, there is no limit. The default is to use half the current
terminal width.


* `marker_extras_<begin/end>`: The strings used to enclose the extra help text
(choices, default values etc.). The defaults are `(` and `)`.


* `marker_choices_<begin/end>`: The strings used to enclose the list of choices for
an argument. The defaults are `{` and `}`.


* `marker_choices_sep`: The string used to separate individual choices in the choice
list. The default is `/`.


* `show_full_help`: Whether to show the full help, including choices, indicators for
required arguments, and the usage string. The default is `True`.

Formatting of individual arguments can be customized with magic attributes defined
on the argument type. The following attributes are recognized:


* `__metavar__`: This can be set to a string on the argument type to override the

    default metavar. Example:

    ```python
    >>> class T:
    ...     __metavar__ = "METAVAR"

    >>> parser = ArgumentParser(
    ...     formatter_class=CorgyHelpFormatter,
    ...     add_help=False,
    ...     usage=argparse.SUPPRESS,
    ... )
    >>> _ = parser.add_argument("--arg", type=T)
    >>> parser.print_help()
    options:
      --arg METAVAR  (default: None)
    ```


#### _property_ using_colors()
Whether colors are enabled.


#### _class_ ShortHelpAction(option_strings, dest, nargs=None, const=None, default=None, type=None, choices=None, required=False, help=None, metavar=None)
`argparse.Action` that displays the short help, and exits.


#### \__call__(parser, namespace, values, option_string=None)
Call self as a function.


#### _class_ FullHelpAction(option_strings, dest, nargs=None, const=None, default=None, type=None, choices=None, required=False, help=None, metavar=None)
`argparse.Action` that displays the full help, and exits.


#### \__call__(parser, namespace, values, option_string=None)
Call self as a function.


#### _classmethod_ add_short_full_helps(parser, short_help_flags=('-h', '--help'), full_help_flags=('--helpfull',), short_help_msg='show help message and exit', full_help_msg='show full help message and exit')
Add arguments for displaying the short or full help.

The parser must be created with `add_help=False` to prevent a clash with the
added arguments.


* **Parameters**


    * **parser** – `ArgumentParser` instance to add the arguments to.


    * **short_help_flags** – Sequence of argument strings for the short help option.
    Default is `("-h", "--help")`.


    * **full_help_flags** – Sequence of argument strings for the full help option.
    Default is `("--helpfull")`.


    * **short_help_msg** – String to describe the short help option. Default is `"show
    help message and exit"`.


    * **full_help_msg** – String to describe the full help option. Default is `"show
    full help message and exit"`.


Example:

```python
>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )
>>> CorgyHelpFormatter.add_short_full_helps(parser)
>>> parser.print_help()
options:
  -h/--help   show help message and exit
  --helpfull  show full help message and exit
```

## Subpackages


* [corgy.types package](corgy.types.md)
