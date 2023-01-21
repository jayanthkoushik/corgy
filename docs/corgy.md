# corgy package

Corgy package for elegant command line parsing.


### _class_ corgy.Corgy(\*\*args)
Base class for collections of variables.

To use, subclass `Corgy`, and declare arguments using type annotations:

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

Attribute values are type-checked, and `ValueError` is raised on type mismatch:

```python
a = A(x="1")      # ERROR!
a = A()
a.x = "1"         # ERROR!

class A(Corgy):
    x: int = "1"  # ERROR!
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
`ArgumentParser` objects by the class methods. Alternatively, to disable setting
`__slots__` completely, set `corgy_make_slots` to `False` in the class definition:

```python
class A(Corgy, corgy_make_slots=False):
    y: int

a = A()
a.y = 1  # `Corgy` variable
a.x = 2  # custom variable
```

Names marked with the `ClassVar` type will be added as class variables, and will
not be available as `Corgy` variables:

```python
class A(Corgy):
    x: ClassVar[int] = 3

A.x         # OK (returns `3`)
A.x = 4     # OK
a = A()
a.x         # OK (returns `3`)
a.x = 4     # ERROR!
```

Also note that class variables need to be assigned to a value during
definition, and this value will not be type checked by `Corgy`.

Inheritance works as expected, whether base classes are themselves `Corgy` classes
or not, with sub-classes inheriting the attributes of the base class, and overriding
any redefined attributes:

```python
class A:
    x: int

class B(Corgy, A):
    y: float = 1.0
    z: str

class C(B):
    y: float = 2.0
    z: str
    w: float

c = C()
print(c)  # prints C(x=<unset>, y=2.0, z=<unset>, w=<unset>)
```

Tracking of base class annotations can be disabled by setting `corgy_track_bases` to
`False` in the class definition. Properties will still be inherited following
standard inheritance rules, but `Corgy` will ignore them:

```python
class A:
    x: int

class B(Corgy, A, corgy_track_bases=False):
    y: float = 1.0
    z: str

b = B()
print(b)  # prints B(y=1.0, z=<unset>)
```

`Corgy` classes can themselves be used as a type, to represent a group of
arguments:

```python
class A(Corgy):
    x: int
    y: float

class B(Corgy):
    x: int
    grp: A
```

`Corgy` recognizes a number of special annotations, which are used to control how
the argument is parsed.

**NOTE**: If any of the following annotations are unavailable in the Python version being
used, you can import them from `typing_extensions` (which is available on PyPI).

**Sequence**
`collections.abc.Sequence` can be used to annotate sequences of arbitrary types.
On Python versions below 3.9, `typing.Sequence` must be used instead. Values will be
checked to ensure that elements match the annotated sequence types.

There are a few different ways to use `Sequence`, each resulting in different
validation conditions. The simplest case is a plain (possibly empty) sequence of a
single type:

```python
x: Sequence[int]
x = [1, 2]    # OK
x = []        # OK
x = [1, "2"]  # ERROR!
x = (1, 2)    # OK (any sequence type is allowed)
```

The sequence length can be controlled by the arguments to `Sequence`. However, this
feature is only available in Python 3.9 and above, since `typing.Sequence` only
accepts a single argument.

To specify that a sequence must be non-empty, use:

```python
x: Sequence[int, ...]
x = []  # ERROR! (`x` cannot be empty)
```

Finally, you can specify a fixed-length sequence:

```python
x: Sequence[int, str, float]
x = [1]               # ERROR!
x = [1, "1", 1.0]     # OK
x = [1, "1", 1.0, 1]  # ERROR!
```

**Tuple**
`typing.Tuple` (or `tuple` in Python 3.9+) can be used instead of `Sequence`. The
main difference is that values are restricted to be tuples instead of arbitrary
sequence types. This method is useful in Python versions below 3.9, since
`typing.Tuple` accepts multiple arguments, unlike `typing.Sequence`.

**Literal**
`typing.Literal` can be used to specify that an argument takes one of a fixed set of
values:

```python
x: Literal[0, 1, "2"]
x = 0    # OK
x = "2"  # OK
x = "1"  # ERROR!
```

`Literal` itself can be used as a type, for instance inside a `Sequence`:

```python
x: Sequence[Literal[0, 1, 2], Literal[0, 1, 2]]
```

This is a sequence of length 2, where each element is either 0, 1, or 2.

Choices can also be specified by adding a `__choices__` attribute to the argument
type, containing a sequence of choices:

```python
class T(int):
    __choices__ = (1, 2)

x: A
x = 1  # OK
x = 3  # ERROR!
```

Note that choices specified in this way are not type-checked to ensure that they
match the argument type.


#### _classmethod_ add_args_to_parser(parser, name_prefix='', flatten_subgrps=False, defaults=None)
Add arguments for this class to the given parser.


* **Parameters**


    * **parser** – Argument parser/group to which the class’s arguments will be added.


    * **name_prefix** – Prefix for argument names. Arguments will be named
    `--<name-prefix>:<var-name>`. If custom flags are present,
    `--<name-prefix>:<flag>` will be used instead (one for each flag).


    * **flatten_subgrps** – Whether to add sub-groups to the main parser instead of
    creating argument groups. Note: sub-sub-groups are always added with
    this argument set to `True`, since `argparse` in unable to properly
    display nested group arguments.


    * **defaults** – Optional mapping with default values for arguments. Any value
    specified here will override default values specified in the class.
    Values for groups can be specified either as `Corgy` instances, or as
    individual values using the same syntax as for `__init__`.


Arguments are added based on their type annotations. A number of special
annotations are recognized, and can be used to control the way an argument
is parsed.

**Annotated**:
`typing.Annotated` can be used to add a help message for an argument:

```python
x: Annotated[int, "help for x"]
```

Annotations can also be used to modify the parser flags for the argument. By
default, the argument name is used, prefixed with `--`, and `_` replaced by `-`.
This syntax can also be used to create a positional argument, by specifying a
flag without any leading `-`:

```python
x: Annotated[int, "help for x"]  # flag is `--x`
x: Annotated[int, "help for x", ["-x", "--ex"]]  # flags are `-x/--ex`
x: Annotated[int, "help for x", ["x"]]  # positional argument
```

`Annotated` can accept multiple arguments, but only the first three are used by
`Corgy`. The first argument is the type, the second is the help message, and the
third is a list of flags.

**NOTE**: `Annotated` should always be the outermost annotation for an argument.

**Optional**:
`typing.Optional` can be used to mark an argument as optional:

```python
x: Optional[int]
x: int | None  # Python 3.10+ (can also use `Optional`)
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
`Optional[int]` in the last example, so it is allowed to be `None`:

```python
class A(Corgy):
    x: Optional[int]
    y: int = 0

a = A()
a.x = None  # OK
a.y = None  # ERROR!
```

Arguments which are not marked as optional (because they are not annotated with
`Optional`, and don’t have a default value) will added to the parser with
`required=True`.

Non-sequence positional arguments marked optional will have `nargs` set to `?`,
and will accept a single argument or none.

**bool**
`bool` types (when not in a sequence) are converted to a pair of options:

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

**Sequence**
Sequence types are added to the parser by setting `nargs`. The value for
`nargs` is determined by the sequence type. Plain sequences, such as
`Sequence[int]`, will be added with `nargs=\*`; Non-empty sequences, such as
`Sequence[int, ...]`, will be added with `nargs=+`; Finally, fixed-length
sequences, such as `Sequence[int, int, int]`, will be added with `nargs` set to
the length of the sequence.

In all cases, sequence types can only be added to a parser if they are single
type. Heterogenous sequences, such as `Sequence[int, str]` cannot be added, and
will raise `ValueError`. Untyped sequences, i.e., annotated with only `Sequence`
also cannot be added, and will raise `ValueError`.

**Tuple**
Tuple types are treated similar to sequences, but will convert the list parsed
from the command line to a tuple.

**Literal**
For `Literal` types, the provided values are passed to the `choices` argument
of `ArgumentParser.add_argument`. All values must be of the same type, which
will be inferred from the type of the first value. If the first value has a
`__bases__` attribute, the type will be inferred as the first base type, and
all other choices must be subclasses of that type:

```python
class A: ...
class A1(A): ...
class A2(A): ...

x: Literal[A1, A2]  # inferred type is A
```

**\`__choices__\`**
For types which specify choices by defining `__choices__`, the values are
passed to the `choices` argument as with `Literal`, but no type inference is
performed, and the base type will be used as the argument type.

**Group**
Attributes which are themselves `Corgy` types are treated as argument groups.
Group arguments are added to the command line parser with the group argument
name prefixed. Note that groups will ignore any custom flags when computing the
prefix; elements within the group will use custom flags, but because they are
prefixed with `--`, they will not be positional.

Example:

```python
class G(Corgy):
    x: int = 0
    y: float

class C(Corgy):
    x: int
    g: G

parser = ArgumentParser()
C.add_args_to_parser(parser)  # adds `--x`, `--g:x`, and `--g:y`
# Set default value for `x`.
C.add_args_to_parser(parser, defaults={"x": 1})
# Set default value for `g` using a `Corgy` instance.
# Note that this will override the default value for `x` specified in `G`.
C.add_args_to_parser(parser, defaults={"g": G(x=1, y=2.0)})
# Set default value for `g` using individual values.
C.add_args_to_parser(parser, defaults={"g:y": 2.0})
```

Custom parsers:
Arguments for which a custom parser is defined using `@corgyparser`, will use
that as the argument type. Refer to the documentation for `corgyparser` for
details.

Metavar:
This function will not explicitly pass a value for the `metavar` argument of
`ArgumentParser.add_argument`, unless an argument’s type has a `__metavar__`
attribute, in which case, it will be passed as is. To change the metavar for
arguments with custom parsers, set the `metavar` argument of `corgyparser`.


#### as_dict(recursive=False)
Return the object as a dictionary.

The returned dictionary maps attribute names to their values. Unset attributes
are omitted, unless they have default values.


* **Parameters**

    **recursive** – whether to recursively call `as_dict` on attributes which are
    `Corgy` instances. Otherwise, they are returned as is.



#### load_dict(d)
Load a dictionary into an instance of the class.

All previous attributes are overwritten, including those for which no new
value is provided. Sub-dictionaries will be parsed recursively if the
corresponding attribute already exists, else will be parsed using `from_dict`.
As with `from_dict`, items in the dictionary without corresponding attributes
are ignored.


* **Parameters**

    **d** – Dictionary to load.


Example:

```python
class A(Corgy):
    x: int
    y: str

a = A(x=1)
a.load_dict({"y": "two"})  # `a` is now `A(y="two")`
```


#### _classmethod_ from_dict(d)
Return a new instance of the class using a dictionary.

This is roughly equivalent to `cls(\*\*d)`, with the main exception being that
groups can be specified as dictionaries themselves, and will be processed
recursively.


* **Parameters**

    **d** – Dictionary to create the instance from.


Example:

```python
class A(Corgy):
    x: int
    y: str

class B(Corgy):
    a: A
    x: str

# These are all equivalent.
b = B.from_dict({"x": "three", "a": {"x": 1, "y": "two"}})
b = B.from_dict({"x": "three", "a": A(x=1, y="two")})
b = B(x="three", a=A(x=1, y="two"))
```

Arguments for groups can also be passed directly in the dictionary by prefixing
their names with the group name and a colon:

```python
b = B.from_dict({"x": "three", "a:x": 1, "a:y": "two"})

class C(Corgy):
    b: B

c = C.from_dict({"b:x": "three", "b:a:x": 1, "b:a:x": "two"})
```


#### _classmethod_ parse_from_cmdline(parser=None, defaults=None, \*\*parser_args)
Return an object of the class parsed from command line arguments.


* **Parameters**


    * **parser** – An instance of `argparse.ArgumentParser` or `None`. If `None`, a new
    instance is created.


    * **defaults** – A dictionary of default values for the arguments, passed to
    `add_args_to_parser`. Refer to the docs for `add_args_to_parser` to
    see more details.


    * **parser_args** – Arguments to be passed to `argparse.ArgumentParser()`. Ignored
    if `parser` is not None.



* **Raises**

    **ArgumentError** – Error parsing command line arguments.



#### _classmethod_ parse_from_toml(toml_file, defaults=None)
Parse an object of the class from a toml file.


* **Parameters**


    * **toml_file** – A file-like object containing the class arguments in toml.


    * **defaults** – A dictionary of default values, overriding the any values
    specified in the class.



* **Raises**

    **TOMLDecodeError** – Error parsing the toml file.



### corgy.corgyparser(\*var_names, metavar=None)
Decorate a function as a custom parser for one or more variables.

To use a custom function for parsing an argument with `Corgy`, use this decorator.
Parsing functions must be static, and should only accept a single string argument.
Decorating the function with `@staticmethod` is optional, but prevents type errors.
`@corgyparser` must be the final decorator in the decorator chain.


* **Parameters**


    * **var_names** – The arguments associated with the decorated parser.


    * **metavar** – Keyword only argument to set the metavar when adding the associated
    argument(s) to an `ArgumentParser` instance.


Example:

```python
class A(Corgy):
    time: tuple[int, int, int]
    @corgyparser("time", metavar="int int int")
    @staticmethod
    def parse_time(s):
        return tuple(map(int, s.split(":")))
```

Multiple arguments can be passed to the decorator, and will all be associated with
the same parser:

```python
class A(Corgy):
    x: int
    y: int
    @corgyparser("x", "y")
    @staticmethod
    def parse_x_y(s):
        return int(s)
```

The `@corgyparser` decorator can also be chained to use the same parser for multiple
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

Note: when chaining, the outer-most non-`None` value of `metavar` will be used.


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
    class T:
        __metavar__ = "METAVAR"

    p = ArgumentParser(formatter_class=CorgyHelpFormatter, add_help=False)
    p.add_argument("--arg", type=T)
    p.print_help()

    # Prints:
    # options:
    #   --arg METAVAR  (optional)
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


## Submodules


* [corgy.types module](corgy.types.md)
