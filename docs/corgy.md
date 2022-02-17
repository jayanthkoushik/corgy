# corgy package

Corgy package for elegant command line parsing.


### _class_ corgy.Corgy(\*\*args)
Base class for collections of variables.

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

**NOTE**: If any of the following annotations are unavilable in the Python version being
used, you can import them from `typing_extension` (which is available on PyPI).

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
`Optional[int]` in the last example, so it is allowed to be `None`.

When parsing from the command line, arguments which are not marked as optional
(because they are not marked with `Optional`, and don’t have a default value) will
be required.

**NOTE**: Default values are not type checked, and can be arbitrary objects.

When parsing, non-sequence positional arguments marked optional will have `nargs`
set to `?`, and will accept a single argument or none.

**Sequence**
`collections.abc.Sequence` can be used to specify that an argument accepts multiple
space-separated values. On Python versions below 3.9, `typing.Sequence` must be
used instead.

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

The sequence length can be controlled by the arguments to `Sequence`. However, this
feature is only available in Python 3.9 and above, since `typing.Sequence` only
accepts a single argument.

To specify that a sequence must be non-empty, use:

```python
x: Sequence[int, ...]
```

This will result in `nargs` being set to `+` in the call to
`ArgumentParser.add_argument`.

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


#### _classmethod_ add_args_to_parser(parser, name_prefix='', make_group=False, group_help=None, defaults=None)
Add arguments for this class to the given parser.


* **Parameters**


    * **parser** – `argparse.ArgumentParser` instance.


    * **name_prefix** – Prefix for argument names (default: empty string). Arguments
    will be named `--<name-prefix>:<var-name>`. If custom flags are present,
    `--<name-prefix>:<flag>` will be used instead (one for each flag).


    * **make_group** – If `True`, the arguments will be added to a group within the
    parser, and `name_prefix` will be used as the group name.


    * **group_help** – Help text for the group. Ignored if `make_group` is `False`.


    * **defaults** – Optional mapping with default values for arguments. Any value
    specified here will override default values specified in the class.
    Values for groups can be specified either as `Corgy` instances, or as
    individual values using the same syntax as for `__init__`.


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


#### as_dict()
Return the object as a dictionary.

The returned dictionary maps attribute names to their values. Unset attributes
are omitted, unless they have default values. This method is not recursive, and
attributes which are `Corgy` instances are returned as is.


#### _classmethod_ parse_from_cmdline(parser=None, defaults=None, \*\*parser_args)
Parse an object of the class from command line arguments.


* **Parameters**


    * **parser** – An instance of `argparse.ArgumentParser` or `None`. If `None`, a new
    instance is created.


    * **defaults** – A dictionary of default values for the arguments, passed to
    `add_args_to_parser`. Refer to the docs for `add_args_to_parser` to
    see more details.


    * **parser_args** – Arguments to be passed to `argparse.ArgumentParser()`. Ignored
    if `parser` is not None.



### corgy.corgyparser(var_name)
Decorate a function as a custom parser for a variable.

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


#### _classmethod_ add_short_full_helps(parser, short_help_flags=('-h', '--help'), full_help_flags=('--helpfull',), short_help_msg='show help message and exit', full_help_msg='show full help messsage and exit')
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
