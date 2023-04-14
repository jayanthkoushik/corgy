"""Types for use with `corgy` (or standalone with `argparse`).

An object of the types defined in this module can be created by calling the respective
type class with a single string argument. `ValueError` is raised if the argument can not
be converted to the desired type.

Examples::

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
    >>> a_subcls_obj  # doctest: +SKIP
    <B object at 0x106cd93d0>

    >>> import argparse
    >>> from argparse import ArgumentParser
    >>> from corgy import CorgyHelpFormatter
    >>> from corgy.types import InputFile
    >>> parser = ArgumentParser(
    ...     formatter_class=CorgyHelpFormatter,
    ...     add_help=False,
    ...     usage=argparse.SUPPRESS,
    ... )
    >>> _ = parser.add_argument("--f", type=InputFile)
    >>> parser.print_help()
    options:
      --f file  (default: None)

"""

from ._initargs import *
from ._inputfile import *
from ._keyvaluepairs import *
from ._outputfile import *
from ._subclass import *

# pylint: disable=undefined-variable
__all__ = (
    _outputfile.__all__  # type: ignore
    + _inputfile.__all__  # type: ignore
    + _subclass.__all__  # type: ignore
    + _keyvaluepairs.__all__  # type: ignore
    + _initargs.__all__  # type: ignore
)
