from __future__ import annotations

import os
import sys
from functools import partial
from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import StrPath

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


def _expand_mixin_base(class_: Type, mod_new: bool) -> Type:
    """Mixin to add support for expanding user directory and environment variables.

    Two concrete implementations of this mixin are provided: `_expand_with_new` and
    `_expand_with_init`. The former is used for classes that have a custom `__new__`
    method, and the latter is used for classes that have a custom `__init__` method.

    The mixins are used as decorators. For example::

        >>> @_expand_with_new  # doctest: +SKIP
        ... class ReadableFile(Path):
        ...     def __new__(cls, path):
        ...         ...

    """
    # Extra docstring to add to the class.
    doc_extra = """

    User directory and environment variable expansion is performed on the path.
    To disable this behavior, set class attributes `do_expanduser` and `do_expandvars`
    to `False` respectively."""

    class ExpandMixin(class_):
        do_expanduser: bool = True
        do_expandvars: bool = True

        @classmethod
        def _do_expand(cls, path: StrPath) -> StrPath:
            if cls.do_expanduser:
                path = os.path.expanduser(path)
            if cls.do_expandvars:
                path = os.path.expandvars(path)
            return path

        if mod_new:

            def __new__(cls: Type[Self], path: StrPath) -> Self:
                path = cls._do_expand(path)
                return super().__new__(cls, path)

        else:

            def __init__(self: Self, path: StrPath) -> None:
                path = self._do_expand(path)
                super().__init__(path)

    base_doc = getattr(class_, "__doc__", "")
    ExpandMixin.__doc__ = base_doc + doc_extra if base_doc else doc_extra.lstrip()

    # Make `ExpandMixin` look like `class`.
    ExpandMixin.__name__ = class_.__name__
    ExpandMixin.__qualname__ = class_.__qualname__
    ExpandMixin.__module__ = class_.__module__
    ExpandMixin.__slots__ = class_.__slots__

    return ExpandMixin


expand_with_new = partial(_expand_mixin_base, mod_new=True)
expand_with_init = partial(_expand_mixin_base, mod_new=False)
