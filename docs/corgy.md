# corgy package

Corgy package for elegant command line parsing.


### _class_ corgy.Corgy(\*\*args)
Base class for collections of variables.

**NOTE**: This class is only available on Python 3.9 or higher.

To create a command line interface, subclass `Corgy`, and declare your arguments
using type annotations:

```python
class A(Corgy):
    x: int
    y: float
```

At runtime, class `A` will have `x`, and `y` as properties, so that the class can be
used similar to Python dataclasses:

```python
a = A()
a.x = 1
a.y  # AttributeError (y is not set)
a.y = a.x + 1.1
```

Note that the class’s `__init__` method only accepts keyword arguments, and ignores
arguments without a corresponding attribute. The following are all valid:

```python
A(x=1, y=2.1)
A(x=1, z=3)  # y is not set, and z is ignored
A(**{"x": 1, "y": 2.1, "z": 3})
```

For command line parsing, the `add_args_to_parser` class method can be used to add
arguments to an `ArgumentParser` object. Refer to the method’s documentation for
more details. `A.add_args_to_parser(parser)` is roughly equivalent to:

```python
parser.add_argument("--x", type=int, required=True)
parser.add_argument("--y", type=float, required=True)
```

`Corgy` classes have their `__slots__` attribute set to the annotated arguments.
So, if you want to use additional instance variables not tracked by `Corgy`, define
them (and only them) in the `__slots__` attribute:

```python
class A(Corgy):
    __slots__ = ("x",)
    y: float

a = A()
a.y = 1  # `Corgy` variable
a.x = 2  # custom variable
```

To allow arbitrary instance variables, add `__dict__` to `__slots__`. Names added
through custom `__slots__` are not processed by `Corgy`, and will not be added to
`ArgumentParser` objects by the class methods.

`Corgy` recognizes a number of special annotations, which are used to control how
the argument is parsed.

**Annotated**:
`typing.Annotated` can be used to add a help message:

```python
x: Annotated[int, "help for x"]
```

Annotations can also be used to modify the flags used to parse the argument. By
default, the argument name is used, prefixed with `--`, and `_` replaced by `-`.
This syntax can also be used to create a positional argument, by specifying a flag
without any leading `-`:

```python
x: Annotated[int, "help for x"]  # flag is `--x`
x: Annotated[int, "help for x", ["-x", "--ex"]]  # flags are `-x/--ex`
x: Annotated[int, "help for x", ["x"]]  # positional argument
```

`Annotated` can accept multiple arguments, but only the first three are used by
`Corgy`. The first argument is the type, the second is the help message, and the
third is a list of flags. `Annotated` should always be the outermost annotation;
other special annotations should be part of the type.

**Optional**:
`typing.Optional` can be used to mark an argument as optional:

```python
x: Optional[int]
```

Another way to mark an argument as optional is to provide a default value:

```python
x: int = 0
```

Default values can be used in conjunction with `Optional`:

```python
x: Optional[int] = 0
```

Note that the last two examples are not equivalent, since the type of `x` is
`Optional[int]` in the last example, so it is allowed to be `None`.

When parsing from the command line, arguments which are not marked as optional
(because they are not marked with `Optional`, and don’t have a default value) will
be required.

**NOTE**: Default values are not type checked, and can be arbitrary objects.

**Sequence**
`collections.abc.Sequence` can be used to specify that an argument accepts multiple
space-separated values. `typing.Sequence` can also be used, but is not recommended
as it is deprecated since Python 3.9.

There are a few different ways to use `Sequence`, each resulting in different
conditions for the parser. The simplest case is a plain sequence:

```python
x: Sequence[int]
```

This represents a (possibly empty) sequence, and corresponds to the following call
to `ArgumentParser.add_argument`:

```python
parser.add_argument("--x", type=int, nargs="*", required=True)
```

Note that since the argument is required, parsing an empty list will still require
`--x` in the command line. After parsing, `x` will be a `list`. To denote an
optional sequence, use `Optional[Sequence[...]]`.

To specify that a sequence must be non-empty, use:

```python
x: Sequence[int, ...]
```

This will result in `nargs` being set to `+` in the call to
`ArgumentParser.add_argument`. Using this syntax **requires**
`collections.abc.Sequence`, since `typing.Sequence` does not accept `...` as an
argument.

Finally, you can specify a fixed length sequence:

```python
x: Sequence[int, int, int]
```

This amounts to `nargs=3`. All types in the sequence must be the same. So,
`Sequence[int, str, int]` will result in a `TypeError`.

**Literal**
`typing.Literal` can be used to specify that an argument takes one of a fixed set of
values:

```python
x: Literal[0, 1, 2]
```

The provided values are passed to the `choices` argument of
`ArgumentParser.add_argument`. All values must be of the same type, which will be
inferred from the type of the first value. If the first value has a `__bases__`
attribute, the type will be inferred as the first base type, and all other choices
must be subclasses of that type:

```python
class A: ...
class A1(A): ...
class A2(A): ...

x: Literal[A1, A2]  # inferred type is A
```

`Literal` itself can be used as a type, for instance inside a `Sequence`:

```python
x: Sequence[Literal[0, 1, 2], Literal[0, 1, 2]]
```

This is a sequence of length 2, where each element is either 0, 1, or 2.

Choices can also be specified by adding a `__choices__` attribute to the argument
type, containing a sequence of choices for the type Note that this will not be type
checked:

```python
class A:
    __choices__ = ("a1", "a2")

x: A
```

**Bool**
`bool` types (when not in a sequence) are converted to
`argparse.BooleanOptionalAction`:

```python
class A(Corgy):
    arg: bool

parser = ArgumentParser()
A.add_to_parser(parser)
parser.print_help()
```

Output:

```text
usage: -c [-h] --arg | --no-arg

optional arguments:
-h, --help       show this help message and exit
--arg, --no-arg
```

Finally, `Corgy` classes can themselves be used as a type, to represent a group of
arguments:

```python
class A(Corgy):
    x: int
    y: float

class B(Corgy):
    x: int
    grp: Annotated[A, "a group"]
```

Group arguments are added to the command line parser with the group argument name
prefixed. In the above example, parsing using `B` would result in the arguments
`--x`, `--grp:x`, and `--grp:y`. `grp:x` and `grp:y` will be converted to an
instance of `A`, and set as the `grp` property of `B`. Note that groups will ignore
any custom flags when computing the prefix; elements within the group will use
custom flags, but because they are prefixed with `--`, they will not be positional.

If initializing a `Corgy` class with `__init__`, arguments for groups can be passed
with their names prefixed with the group name and a colon:

```python
class C(Corgy):
    x: int

class D(Corgy):
    x: int
    c: C

d = D(**{"x": 1, "c:x": 2})
d.x  # 1
d.c  # C(x=2)
```


#### _classmethod_ add_args_to_parser(parser, name_prefix='', make_group=False, group_help=None)
Add arguments for this class to the given parser.


* **Parameters**


    * **parser** – `argparse.ArgumentParser` instance.


    * **name_prefix** – Prefix for argument names (default: empty string). Arguments
    will be named `--<name-prefix>:<var-name>`. If custom flags are present,
    `--<name-prefix>:<flag>` will be used instead (one for each flag).


    * **make_group** – If `True`, the arguments will be added to a group within the
    parser, and `name_prefix` will be used as the group name.


    * **group_help** – Help text for the group. Ignored if `make_group` is `False`.



#### _classmethod_ parse_from_cmdline(parser=None, \*\*parser_args)
Parse an object of the class from command line arguments.


* **Parameters**


    * **parser** – An instance of `argparse.ArgumentParser` or `None`. If `None`, a new
    instance is created.


    * **parser_args** – Arguments to be passed to `argparse.ArgumentParser()`. Ignored
    if `parser` is not None.



### corgy.corgyparser(var_name)
Decorate a function as a custom parser for a variable.

**NOTE**: This decorator is only available on Python 3.9 or higher.

To use a custom function for parsing an argument with `Corgy`, use this decorator.
Parsing functions must be static, and should only accept a single string argument.
Decorating the function with `@staticmethod` is optional, but prevents type errors.
`@corgyparser` must be the final decorator in the decorator chain.


* **Parameters**

    **var_name** – The argument associated with the decorated parser.


Example:

```python
class A(Corgy):
    time: tuple[int, int, int]
    @corgyparser("time")
    @staticmethod
    def parse_time(s):
        return tuple(map(int, s.split(":")))
```

The `@corgyparser` decorator can be chained to use the same parser for multiple
arguments:

```python
class A(Corgy):
    x: int
    y: int
    @corgyparser("x")
    @corgyparser("y")
    @staticmethod
    def parse_x_y(s):
        return int(s)
```


### _class_ corgy.CorgyHelpFormatter(prog)
Formatter class for `argparse` with a cleaner layout, and support for colors.

`Corgy.parse_from_cmdline` uses this formatter by default, unless a different
`formatter_class` argument is provided. `CorgyHelpFormatter` can also be used
independently of `Corgy`. Simply pass it as the `formatter_class` argument to
`argparse.ArgumentParser()`:

```python
from argparse import ArgumentParser
from corgy import CorgyHelpFormatter
parser = ArgumentParser(formatter_class=CorgyHelpFormatter)
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
start from. If `None`, there is no limit. The default is `40`.


* `marker_extras_<begin/end>`: The strings used to enclose the extra help text
(choices, default values etc.). The defaults are `(` and `)`.


* `marker_choices_<begin/end>`: The strings used to enclose the list of choices for
an argument. The defaults are `{` and `}`.


* `marker_choices_sep`: The string used to separate individual choices in the choice
list. The default is `/`.

Formatting of individual arguments can be customized with magic attributes defined
on the argument type. The following attributes are recognized:


* `__metavar__`: This can be set to a string on the argument type to override the

    default metavar. Usage:

    ```python
    >>> class T:
            __metavar__ = "METAVAR"
    >>> p = ArgumentParser(formatter_class=CorgyHelpFormatter, add_help=False)
    >>> p.add_argument("--arg", type=T)
    >>> p.print_help()
    options:
      --arg METAVAR  (optional)
    ```


* `__corgy_fmt_choice__`: Formatting of argument choices/defaults can be customized

    by defining a function of this name on the argument type. The function should
    take a single argument, the choice, and return a string. Usage:

    ```python
    >>> class T:
        @staticmethod
        def __corgy_fmt_choice__(choice):
            return f"CHOICE-{choice}"
    >>> p = ArgumentParser(formatter_class=CorgyHelpFormatter, add_help=False)
    >>> p.add_argument("--arg", type=T, choices=["a", "b", "c"], default="a")
    >>> p.print_help()
    options:
      --arg T  ({CHOICE-a/CHOICE-b/CHOICE-c} default: CHOICE-a)
    ```


#### _property_ using_colors()
Whether colors are enabled.

## Submodules

## corgy.types module

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
