#!/usr/bin/env sh
# Usage: docs/make.sh  # must be executed from the project root
# Generates markdown documentation for each top level package, except `tests`.
# One file is generated per package, which is put in `docs/`.

SPHINX_APIDOC_OPTIONS='members' \
    poetry run sphinx-apidoc -o "docs/_build" -M -T . tests

for f in docs/_build/*.rst ; do
    rootdoc="$(basename "${f}" .rst)"
    poetry run sphinx-build \
        -D highlight_language=python \
        -D root_doc="${rootdoc}" \
        -b markdown \
        -c "docs" \
        -d "docs/_build/.doctrees" \
        "docs/_build" "docs"

    # Remove trailing whitespace.
    sed -i '' 's/ *$//' "docs/${rootdoc}.md"
done
