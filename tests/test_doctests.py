import doctest

import corgy

DOCTEST_FILES = ["_corgy.py", "_helpfmt.py", "types.py"]


def load_tests(loader, tests, ignore):
    for _file in DOCTEST_FILES:
        tests.addTest(doctest.DocFileSuite(_file, package=corgy))
    tests.addTest(doctest.DocFileSuite("../README.md"))
    return tests
