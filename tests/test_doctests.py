import doctest
import sys

import corgy

DOCTEST_FILES = ["_corgy.py", "_helpfmt.py", "types.py"]


def load_tests(loader, tests, ignore):
    for _file in DOCTEST_FILES:
        tests.addTest(doctest.DocFileSuite(_file, package=corgy))
    if sys.version_info < (3, 11):
        # Skip README doctest for Python 3.11+ since `typing_extensions` is
        # not installed as a dependency.
        tests.addTest(doctest.DocFileSuite("../README.md"))
    return tests
