import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

# Functions to create temporary files and directories created in the home
# directory, or at a path specified by an environment variable.


@contextmanager
def temp_file_in_home(testcase: TestCase):
    """Get a temporary file (or directory) in the home directory."""
    try:
        d = TemporaryDirectory(dir=Path.home())
        fpath = os.path.join(d.name, "temp.file")
        with open(fpath, "wb"):
            pass
        yield Path(fpath)
    except OSError as e:
        testcase.skipTest(f"could not create temp file in home: {e}")
    finally:
        d.cleanup()


@contextmanager
def temp_dir_in_home(testcase: TestCase):
    """Get a temporary directory in the home directory."""
    try:
        d = TemporaryDirectory(dir=Path.home())
        yield Path(d.name)
    except OSError as e:
        testcase.skipTest(f"could not create temp dir in home: {e}")
    finally:
        d.cleanup()


@contextmanager
def temp_env_var_file(testcase: TestCase):
    """Get a temporary file and set an environment variable to its name."""
    # Get a random string to use as the environment variable name
    env_var = f"CORGY_TEMP_{os.urandom(8).hex()}"
    with TemporaryDirectory() as d:
        fpath = os.path.join(d, "temp.file")
        with open(fpath, "wb"):
            pass
        os.environ[env_var] = fpath
        try:
            yield env_var, Path(fpath)
        finally:
            del os.environ[env_var]


@contextmanager
def temp_env_var_dir(testcase: TestCase):
    """Get a temporary directory and set an environment variable to its name."""
    # Get a random string to use as the environment variable name
    env_var = f"CORGY_TEMP_{os.urandom(8).hex()}"
    with TemporaryDirectory() as d:
        os.environ[env_var] = d
        try:
            yield env_var, Path(d)
        finally:
            del os.environ[env_var]
