from __future__ import annotations

import sys
from typing import TypeVar

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

__all__ = ("Required", "NotRequired")

# `Required` and `NotRequired` are implemented as `Annotated` types.
# These are used to mark attributes as required or not required.
_T = TypeVar("_T")

REQUIRED = object()
Required = Annotated[_T, REQUIRED]

NOT_REQUIRED = object()
NotRequired = Annotated[_T, NOT_REQUIRED]
