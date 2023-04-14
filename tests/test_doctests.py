import sys
from doctest import DocFileSuite

import corgy
import corgy.types

DOCTEST_MODULES = {
    corgy: ["_corgy.py", "_corgyparser.py", "_helpfmt.py"],
    corgy.types: [
        "_initargs.py",
        "_inputfile.py",
        "_keyvaluepairs.py",
        "_outputfile.py",
        "_subclass.py",
    ],
}

DOCTEST_FILES = ["../README.md"]


def load_tests(loader, tests, ignore):
    for mod, modfiles in DOCTEST_MODULES.items():
        for file in modfiles:
            tests.addTest(DocFileSuite(file, package=mod))

    if sys.version_info < (3, 11):
        # Skip README doctest for Python 3.11+ since `typing_extensions` is
        # not installed as a dependency.
        for file in DOCTEST_FILES:
            tests.addTest(DocFileSuite(file))

    return tests
