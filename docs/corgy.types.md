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
is raised if any of the operations fail.


### _class_ corgy.types.OutputBinFile(path)
Type for an output binary file.


* **Parameters**

    **path** – Path to a file.


This class is a thin wrapper around `BufferedWriter` that accepts a path, instead
of a file stream. The file will be created if it does not exist (including any
parent directories), and opened in binary mode. Existing files will be truncated.
`ArgumentTypeError` is raised if any of the operations fail.


### _class_ corgy.types.InputTextFile(path, \*\*kwargs)
`TextIOWrapper` sub-class representing an input file.


* **Parameters**


    * **path** – Path to a file.


    * **kwargs** – Keyword only arguments that are passed to `TextIOWrapper`.


The file must exist, and will be opened in text mode (`r`). `ArgumentTypeError` is
raised if this fails.


### _class_ corgy.types.InputBinFile(path)
Type for an input binary file.


* **Parameters**

    **path** – Path to a file.


This class is a thin wrapper around `BufferedReader` that accepts a path, instead
of a file stream. The file must exist, and will be opened in binary mode.
`ArgumentTypeError` is raised if this fails.


### _class_ corgy.types.OutputDirectory(path)
`Path` sub-class representing a directory to be written to.


* **Parameters**

    **path** – Path to a directory.


If the path does not exist, a directory with the path name will be created
(including any parent directories). `ArgumentTypeError` is raised if this fails, or
if the path is not a directory, or if the directory is not writable.


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


### _class_ corgy.types.KeyValuePairs(values)
Dictionary sub-class that is initialized from a string of key-value pairs.

Example:

```python
>>> MapType = KeyValuePairs[str, int]
>>> map = MapType("a=1,b=2")
>>> map
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