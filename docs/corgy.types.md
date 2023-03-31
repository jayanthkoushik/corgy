# corgy.types package

Types for use with `corgy` (or standalone with `argparse`).

An object of the types defined in this module can be created by calling the respective
type class with a single string argument. `ValueError` is raised if the argument can not
be converted to the desired type.

Examples:

```python
>>> from corgy.types import KeyValuePairs
>>> StrIntMapType = KeyValuePairs[str, int]
>>> str_int_map = StrIntMapType("a=1,b=2")
>>> print(str_int_map)
{'a': 1, 'b': 2}

>>> class A: ...
>>> class B(A): ...
>>> class C(A): ...

>>> from corgy.types import SubClass
>>> ASubClsType = SubClass[A]
>>> a_subcls = ASubClsType("B")
>>> a_subcls_obj = a_subcls()
>>> a_subcls_obj
<B object at 0x106cd93d0>

>>> import argparse
>>> from argparse import ArgumentParser
>>> from corgy import CorgyHelpFormatter
>>> from corgy.types import InputDirectory
>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )
>>> _ = parser.add_argument("--d", type=InputDirectory)
>>> parser.print_help()
options:
  --d dir  (default: None)
```


### _class_ corgy.types.ReadableFile(path)
`Path` sub-class representing a readable file.


* **Parameters**

    **path** – String or path-like object.


The provided path must point to an existing file, and the file must be readable.
`ValueError` is raised otherwise.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.WritableFile(path)
`Path` sub-class representing a writable file.


* **Parameters**

    **path** – String or path-like object.


If the path exists, it must be a file, and it must be writable. If the path does
not exist, the path’s directory must exist and be writable. `ValueError` is
raised otherwise.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.OutputTextFile(path)
`TextIOWrapper` sub-class representing an output file.


* **Parameters**

    **path** – Path to a file.


The file will be created if it does not exist (including any parent directories),
and opened in text mode (`w`). Existing files will be truncated. `ValueError`
is raised if any of the operations fail. An `atexit` handler will be registered to
close the file on program termination.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.OutputBinFile(path)
Type for an output binary file.


* **Parameters**

    **path** – Path to a file.


This class is a thin wrapper around `BufferedWriter` that accepts a path, instead
of a file stream. The file will be created if it does not exist (including any
parent directories), and opened in binary mode. Existing files will be truncated.
`ValueError` is raised if any of the operations fail. An `atexit` handler
will be registered to close the file on program termination.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.LazyOutputTextFile(path)
`OutputTextFile` sub-class that does not auto-initialize.

Useful for “default” files, which only need to be created if an alternative is not
provided. `init` must be called on instances before they can be used.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.LazyOutputBinFile(path)
`OutputBinFile` sub-class that does not auto-initialize.

Useful for “default” files, which only need to be created if an alternative is not
provided. `init` must be called on instances before they can be used.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.InputTextFile(path)
`TextIOWrapper` sub-class representing an input file.


* **Parameters**

    **path** – Path to a file.


The file must exist, and will be opened in text mode (`r`). `ValueError` is
raised if this fails. An `atexit` handler will be registered to close the file on
program termination.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.InputBinFile(path)
Type for an input binary file.


* **Parameters**

    **path** – Path to a file.


This class is a thin wrapper around `BufferedReader` that accepts a path, instead
of a file stream. The file must exist, and will be opened in binary mode.
`ValueError` is raised if this fails. An `atexit` handler will be registered
to close the file on program termination.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.OutputDirectory(path)
`Path` sub-class representing a directory to be written to.


* **Parameters**

    **path** – Path to a directory.


If the path does not exist, a directory with the path name will be created
(including any parent directories). `ValueError` is raised if this fails, or
if the path is not a directory, or if the directory is not writable.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.LazyOutputDirectory(path)
`OutputDirectory` sub-class that does not auto-initialize.

Useful for “default” folders, which only need to be created if an alternative is not
provided. `init` must be called on instances to ensure that the directory exists.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.InputDirectory(path)
`Path` sub-class representing a directory to be read from.


* **Parameters**

    **path** – Path to a directory.


The directory must exist, and will be checked to ensure it is readable.
`ValueError` is raised if this is not the case.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.IODirectory(path)
`Path` sub-class representing an existing directory to be read from/written to.


* **Parameters**

    **path** – Path to a directory.


The directory must exist, and will be checked to ensure it is readable and
writeable. `ValueError` is raised if this is not the case.

User directory and environment variable expansion is performed on the path.
To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
to `False` respectively.


### _class_ corgy.types.SubClass(name)
Type representing a sub-class of a given class.

Example:

```python
>>> from corgy.types import SubClass

>>> class Base: ...
>>> class Sub1(Base): ...
>>> class Sub2(Base): ...

>>> BaseSubType = SubClass[Base]   # type for a sub-class of `Base`
>>> BaseSub = BaseSubType("Sub1")  # sub-class of `Base` named `Sub1`
>>> base_sub = BaseSub()           # instance of a sub-class of `Base`
>>> base_sub
<Sub1 object at 0x100ea40a0>
```

This class cannot be called directly. It first needs to be associated with a base
class, using the `SubClass[Base]` syntax. This returns a new `SubClass` type, which
is associated with `Base`. The returned type is callable, and accepts the name of a
sub-class of `Base`. So, `SubClass[Base]("Sub1")` returns a `SubClass` type instance
corresponding to the sub-class `Sub1` of `Base`. Finally, the `SubClass` instance
can be called to create an instance of the sub-class, e.g.,
`SubClass[Base]("Sub1")()`.

This class is useful for creating objects of a generic class, where the concrete
class is determined at runtime, e.g, by a command-line argument:

```python
>>> from argparse import ArgumentParser

>>> parser = ArgumentParser()
>>> _ = parser.add_argument("--base-subcls", type=SubClass[Base])

>>> args = parser.parse_args(["--base-subcls", "Sub1"])
>>> base_obj = args.base_subcls()  # an instance of a sub-class of `Base`
```

For further convenience when parsing command-line arguments, the class provides a
`__choices__` property, which returns a tuple of all valid sub-classes, and can be
passed as the `choices` argument to `ArgumentParser.add_argument`. Refer to the
docstring of `__choices__` for more information.


* **Parameters**

    **name** – Name of the sub-class.


The behavior of sub-class type identification can be customized by setting class
attributes (preferably on the type returned by the `[...]` syntax).


* `allow_base`: If `True`, the base class itself will be allowed as a valid

    sub-class. The default is `False`. Example:

    ```python
    >>> class Base: ...
    >>> class Sub1(Base): ...
    >>> class Sub2(Base): ...
    >>> T = SubClass[Base]
    >>> T.__choices__
    (SubClass[Base]('Sub1'), SubClass[Base]('Sub2'))
    >>> T.allow_base = True
    >>> T.__choices__
    (SubClass[Base]('Base'), SubClass[Base]('Sub1'), SubClass[Base]('Sub2'))
    ```


* `use_full_names`: If `True`, the name passed to the constructor needs to be the

    full name of a sub-class, given by `cls.__module__ + "." + cls.__qualname__`. If
    `False` (the default), the name needs to just be `cls.__name__`. This is useful
    if the sub-classes are not uniquely identified by just their names.


* `allow_indirect_subs`: If `True` (the default), indirect sub-classes, i.e.,

    sub-classes of the base through another sub-class, are allowed. If `False`,
    only direct sub-classes of the base are allowed. Example:

    ```python
    >>> class Base: ...
    >>> class Sub1(Base): ...
    >>> class Sub2(Sub1): ...
    >>> T = SubClass[Base]
    >>> T.__choices__
    (SubClass[Base]('Sub1'), SubClass[Base]('Sub2'))
    >>> T.allow_indirect_subs = False
    >>> T.__choices__
    (SubClass[Base]('Sub1'),)
    ```

Note that the types returned by the `SubClass[...]` syntax are cached using the
base class type. So all instances of `SubClass[Base]` will return the same type,
and any attributes set on the type will be shared between all instances.


#### _property_ which()
Return the class represented by the `SubClass` instance.


#### _class property_ \__choices__()
Return a tuple of `SubClass` instances for valid sub-classes of the base.

Each item in the tuple is an instance of `SubClass`, and corresponds to a valid
sub-class of the base-class associated with this type.


#### \__call__(\*args, \*\*kwargs)
Return an instance of the sub-class associated with this type.

Example:

```python
>>> class Base: ...
>>> class Sub1(Base):
...     def __init__(self, x):
...         print(f"initializing `Sub1` with 'x={x}'")

>>> BaseSubType = SubClass[Base]
>>> BaseSub = BaseSubType("Sub1")  # an instance of the `SubClass` type

>>> base_sub = BaseSub(1)
initializing `Sub1` with 'x=1'
```


### _class_ corgy.types.KeyValuePairs(values)
Dictionary sub-class that is initialized from a string of key-value pairs.

Example:

```python
>>> from corgy.types import KeyValuePairs

>>> MapType = KeyValuePairs[str, int]
>>> print(MapType("a=1,b=2"))
{'a': 1, 'b': 2}
```

This class supports the class indexing syntax to specify the types for keys and
values. `KeyValuePairs[KT, VT]` returns a new `KeyValuePairs` type where the key
and value types are `KT` and `VT`, respectively. Using the class directly is
equivalent to using `KeyValuePairs[str, str]`.

When called, the class expects a single string argument, with comma-separated
`key=value` pairs (see below for how to change the separators). The string is
parsed, and a dictionary is created with the keys and values cast to their
respective types. `ValueError` is raised if this fails. This class is
useful for parsing dictionaries from command-line arguments.

By default, the class expects a string of the form `key1=value1,key2=value2,...`.
This can be changed by setting the following class attributes:


* sequence_separator: The string that separates individual key-value pairs. The

    default is `,`.


* item_separator: The string that separates keys and values. The default is `=`.

Note that types returned by the `KeyValuePairs[...]` syntax are cached using the
key and value types:

```python
>>> MapType = KeyValuePairs[str, int]
>>> MapType.sequence_separator = ";"
>>> MapType2 = KeyValuePairs[str, int]  # same as `MapType`
>>> MapType2.sequence_separator
';'
>>> MapType2.sequence_separator = ","
```

`KeyValuePairs` instances can also be initialized with a dictionary. However, note
that the dictionary is not type-checked and is used as-is.


### _class_ corgy.types.InitArgs(\*\*args)
Corgy wrapper around arguments of a class’s `__init__`.

Example:

```python
>>> import argparse
>>> from argparse import ArgumentParser
>>> from typing import Sequence
>>> from corgy import CorgyHelpFormatter
>>> from corgy.types import InitArgs

>>> class Foo:
...     def __init__(
...         self,
...         a: int,
...         b: Sequence[str],
...         c: float = 0.0,
...     ):
...         ...

>>> FooInitArgs = InitArgs[Foo]
>>> parser = ArgumentParser(
...     formatter_class=CorgyHelpFormatter,
...     add_help=False,
...     usage=argparse.SUPPRESS,
... )
>>> FooInitArgs.add_args_to_parser(parser)
>>> parser.print_help()
options:
  --a int        (optional)
  --b [str ...]  (optional)
  --c float      (default: 0.0)

>>> args = parser.parse_args(["--a", "1", "--b", "one", "two"])
>>> foo = Foo(args.a, args.b, args.c)
```

This is a generic class, and on using the `InitArgs[Cls]` syntax, a concrete
`Corgy` class is created, which has attributes corresponding to the arguments of
`Cls.__init__`, with types inferred from annotations. The returned class can be used
as any other `Corgy` class, including as a type annotation within another `Corgy`
class.

All arguments of the `__init__` method must be annotated, following the same rules
as for other `Corgy` classes. Positional only arguments are not supported, since
they are not associated with an argument name. `TypeError` is raised if either of
these conditions is not met.
