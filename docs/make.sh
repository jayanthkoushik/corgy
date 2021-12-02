#!/usr/bin/env sh
# Usage: docs/make.sh  # must be executed from the project root
# Generates markdown documentation for each top level package, except `tests`.
# One file is generated per module, which is put in `docs/`.

SPHINX_APIDOC_OPTIONS='members' \
poetry run sphinx-apidoc \
    -o docs/_build \
    --module-first \
    --tocfile index \
    --separate \
    . tests

poetry run sphinx-build \
    -C \
    -D extensions=sphinx.ext.autodoc,sphinx.ext.napoleon \
    -D default_role=samp \
    -D autodoc_member_order=bysource \
    -D autodoc_typehints=none \
    -D highlight_language=python \
    -b markdown \
    -c docs \
    -d docs/_build/.doctrees \
    docs/_build docs `ls docs/_build/*.rst`

find docs -name '*.md' -exec sed -i '' 's/ *$//' {} +
