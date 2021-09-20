# corgy

Elegant command line parsing for Python.

Corgy allows you to create a command line interface in Python, without worrying about boilerplate code. This results in cleaner, more modular code.

```python
from corgy import Corgy

class ArgGroup(Corgy):
    arg1: Annotated[Optional[int], "optional number"]
    arg2: Annotated[bool, "a boolean"]

class MyArgs(Corgy):
    arg1: Annotated[int, "a number"] = 1
    arg2: Annotated[Sequence[float], "at least one float"]
    grp1: Annotated[ArgGroup, "group 1"]

args = MyArgs.parse_from_cmdline()
```

Compare this to the equivalent code which uses argparse:

```python
from argparse import ArgumentParser, BooleanOptionalAction

parser = ArgumentParser()
parser.add_argument("--arg1", type=int, help="a number", default=1)
parser.add_argument("--arg2", type=float, nargs="+", help="at least one float", required=True)

grp_parser = parser.add_argument_group("group 1")
grp_parser.add_argument("--grp1:arg1", type=int, help="optional number")
grp_parser.add_argument("--grp1:arg2", help="a boolean", action=BooleanOptionalAction)

args = parser.parse_args()
```

Corgy also provides support for more informative help messages from `argparse`, and colorized output:

![Sample output from Corgy](https://raw.githubusercontent.com/jayanthkoushik/corgy/7c0b4c0ad48fb8c1838e3d31a96fdd094fd01ac6/example.svg)

# Install
`corgy` is available on PyPI, and can be installed with pip:

```bash
pip install corgy
```

**The full `corgy` package requires Python 3.9 or higher**. Python 3.7 and 3.8 are also supported, but only have access to `CorgyHelpFormatter`, and `corgy.types`.

Support for colorized output requires the `crayons` package, also available on PyPI. You can pull it as a dependency for `corgy` by installing with the `colors` extra:

```bash
pip install corgy[colors]
```

# Usage
For documentation on usage, refer to docs/index.md.
