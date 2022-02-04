# corgy.types module

Types for use with `corgy` (or standalone with `argparse`).

An object of the types defined in this module can be created by calling the respective
type class with a single string argument. `ArgumentTypeError` is raised if the argument
can not be converted to the desired type.

Examples:

```python
str_int_map: KeyValuePairs[str, int]
str_int_map = KeyValuePairs[str, int]("a=1,b=2")

class A: ...
class B(A): ...
class C(A): ...

a_subcls: SubClass[A]
a_subcls = SubClass[A]("B")
a_subcls_obj = a_subcls()

class Args(Corgy):
    out_file: Annotated[OutputTextFile, "a text file opened for writing"]

parser = ArgumentParser()
parser.add_argument("--in-dir", type=InputDirectory, help="an existing directory")
```


### _class_ corgy.types.OutputTextFile(path, \*\*kwargs)
`TextIOWrapper` sub-class representing an output file.


* **Parameters**


    * **path** – Path to a file.


    * **kwargs** – Keyword only arguments that are passed to `TextIOWrapper`.


The file will be created if it does not exist (including any parent directories),
and opened in text mode (`w`). Existing files will be truncated. `ArgumentTypeError`
is raised if any of the operations fail. An `atexit` handler will be registered to
close the file on program termination.


#### init()
No-op for compatibility with `LazyOutputTextFile`.


#### _class property_ stdout_wrapper()
`sys.__stdout__` wrapped with `TextIOWrapper` (line buffered).


#### _class property_ stderr_wrapper()
`sys.__stderr__` wrapped with `TextIOWrapper` (line buffered).


### _class_ corgy.types.OutputBinFile(path)
Type for an output binary file.


* **Parameters**

    **path** – Path to a file.


This class is a thin wrapper around `BufferedWriter` that accepts a path, instead
of a file stream. The file will be created if it does not exist (including any
parent directories), and opened in binary mode. Existing files will be truncated.
`ArgumentTypeError` is raised if any of the operations fail. An `atexit` handler
will be registered to close the file on program termination.


#### init()
No-op for compatibility with `LazyOutputBinFile`.


### _class_ corgy.types.LazyOutputTextFile(path, \*\*kwargs)
`OutputTextFile` sub-class that does not auto-initialize.

Useful for “default” files, which only need to be created if an alternative is not
provided. `init` must be called on instances before they can be used.


#### init()
Initialize the file.


### _class_ corgy.types.LazyOutputBinFile(path)
`OutputBinFile` sub-class that does not auto-initialize.

Useful for “default” files, which only need to be created if an alternative is not
provided. `init` must be called on instances before they can be used.


#### init()
Initialize the file.


### _class_ corgy.types.InputTextFile(path, \*\*kwargs)
`TextIOWrapper` sub-class representing an input file.


* **Parameters**


    * **path** – Path to a file.


    * **kwargs** – Keyword only arguments that are passed to `TextIOWrapper`.


The file must exist, and will be opened in text mode (`r`). `ArgumentTypeError` is
raised if this fails. An `atexit` handler will be registered to close the file on
program termination.


#### _class property_ stdin_wrapper()
`sys.__stdin__` wrapped with `TextIOWrapper`.


### _class_ corgy.types.InputBinFile(path)
Type for an input binary file.


* **Parameters**

    **path** – Path to a file.


This class is a thin wrapper around `BufferedReader` that accepts a path, instead
of a file stream. The file must exist, and will be opened in binary mode.
`ArgumentTypeError` is raised if this fails. An `atexit` handler will be registered
to close the file on program termination.


### _class_ corgy.types.OutputDirectory(path)
`Path` sub-class representing a directory to be written to.


* **Parameters**

    **path** – Path to a directory.


If the path does not exist, a directory with the path name will be created
(including any parent directories). `ArgumentTypeError` is raised if this fails, or
if the path is not a directory, or if the directory is not writable.


#### init()
No-op for compatibility with `LazyOutputDirectory`.


### _class_ corgy.types.LazyOutputDirectory(path)
`OutputDirectory` sub-class that does not auto-initialize.

Useful for “default” folders, which only need to be created if an alternative is not
provided. `init` must be called on instances to ensure that the directory exists.


#### init()
Initialize the directory.


### _class_ corgy.types.InputDirectory(path)
`Path` sub-class representing a directory to be read from.


* **Parameters**

    **path** – Path to a directory.


The directory must exist, and will be checked to ensure it is readable.
`ArgumentTypeError` is raised if this is not the case.


### _class_ corgy.types.SubClass(name)
Type representing a sub-class of a given class.

Example:

```python
class Base: ...
class Sub1(Base): ...
class Sub2(Base): ...

BaseSubType = SubClass[Base]  # type for a sub-class of `Base`
BaseSub = BaseSubType("Sub1")  # sub-class of `Base` named `Sub1`
base_sub = BaseSub()  # instace of a sub-class of `Base`
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
parser = ArgumentParser()
parser.add_argument("--base-subcls", type=SubClass[Base])
args = parser.parse_args()  # e.g. `--base-subcls Sub1`
base_obj = args.base_subcls()  # an instance of a sub-class of `Base`
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
    BaseSubType = SubClass[Base]
    BaseSubType.allow_base = True
    BaseSub = BaseSubType("Base")  # base class is allowed as a sub-class
    ```


* `use_full_names`: If `True`, the name passed to the constructor needs to be the

    full name of a sub-class, given by `cls.__module__ + "." + cls.__qualname__`. If
    `False` (the default), the name needs to just be `cls.__name__`. This is useful
    if the sub-classes are not uniquely identified by just their names. Example:

    ```python
    BaseSubType = SubClass[Base]
    BaseSubType.use_full_names = True
    BaseSub = BaseSubType("corgy.types.Sub1")
    ```


* `allow_indirect_subs`: If `True` (the default), indirect sub-classes, i.e.,

    sub-classes of the base through another sub-class, are allowed. If `False`,
    only direct sub-classes of the base are allowed. Example:

    ```python
    class SubSub1(Sub1): ...
    BaseSubType = SubClass[Base]
    BaseSubType.allow_indirect_subs = False
    BaseSubType("SubSub1") # fails, `SubSub1` is not a direct sub-class
    ```

Note that the types returned by the `SubClass[...]` syntax are cached using the
base class type. So all instances of `SubClass[Base]` will return the same type,
and any attributes set on the type will be shared between all instances.


#### _class property_ \__choices__()
Return a tuple of `SubClass` instances for valid sub-classes of the base.

Each item in the tuple is an instance of `SubClass`, and corresponds to a valid
sub-class of the base-class associated with this type.


#### \__call__(\*args, \*\*kwargs)
Return an instance of the sub-class associated with this type.

Example:

```python
class Base: ...
class Sub1(Base): ...

BaseSubType = SubClass[Base]
BaseSub = BaseSubType("Sub1")  # an instance of the `SubClass` type

base_sub = BaseSub()  # an instance of `Sub1`
```


### _class_ corgy.types.KeyValuePairs(values)
Dictionary sub-class that is initialized from a string of key-value pairs.

Example:

```python
>>> MapType = KeyValuePairs[str, int]
>>> map = MapType("a=1,b=2")
>>> print(map)
{'a': 1, 'b': 2}
```

This class supports the class indexing syntax to specify the types for keys and
values. `KeyValuePairs[KT, VT]` returns a new `KeyValuePairs` type where the key
and value types are `KT` and `VT`, respectively. Using the class directly is
equivalent to using `KeyValuePairs[str, str]`.

When called, the class expects a single string argument, with comma-separated
`key=value` pairs (see below for how to change the separators). The string is
parsed, and a dictionary is created with the keys and values cast to their
respective types. `ArgumentTypeError` is raised if this fails. This class is
useful for parsing dictionaries from command-line arguments.

By default, the class expects a string of the form `key1=value1,key2=value2,...`.
This can be changed by setting the following class attributes:


* sequence_separator: The string that separates indidivual key-value pairs. The

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
```

`KeyValuePairs` instances can also be initialized with a dictionary. However, note
that the dictionary is not type-checked and is used as-is:

```python
>>> dic = KeyValuePairs[str, int]({"a": 1, "b": 2})
>>> repr(dic)
>>> KeyValuePairs[str, int]({'a': 1, 'b': 2})
```


### _class_ corgy.types.InitArgs(\*\*args)
Corgy wrapper around arguments of a class’s `__init__`.

Example:

```python
$ cat test.py
class Foo:
    def __init__(
        self,
        a: Annotated[int, "a help"],
        b: Annotated[Sequence[str], "b help"],
        c: Annotated[float, "c help"] = 0.0,
    ):
        ...
FooInitArgs = InitArgs[Foo]
foo_init_args = FooInitArgs.parse_from_cmdline()
foo = Foo(**foo_init_args.as_dict())

$ python test.py --help
usage: test.py [-h] --a int --b [str ...] [--c float]

options:
  -h/--help      show this help message and exit
  --a int        a help (required)
  --b [str ...]  b help (required)
  --c float      c help (default: 0.0)
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
