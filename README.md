# Project Initialization Checklist

1. Replace templates
  + Rename `PROJECT` folder
  + Update `pyproject.toml` (templates are enclosed in `<<` and `>>`):
    - Fix `name`, `description`, and `repository`
    - Fix package name in `packages = ...`
    - Optional: Add keywords and trove classifiers
  + Create `.github/workflows` and move needed workflows from `.github/workflow-templates`
    - If including the `pypi-publish` workflow, create `PYPI_PASSWORD` GitHub secret with the PyPI password

2. Set up environment
  + Ensure the following are installed: poetry, standard-version, conventional-github-releaser, commitlint
  * Install jq if working with jupyter notebooks (needed for nbstrip hook)
  + Create Python virtual env
  + Add dependencies to `pyproject.toml`
  + Install basic dependencies: `poetry install`
  + Install git hooks: `pre-commit install -t pre-commit -t commit-msg`

3. Push changes
  + Update `README.md`
  + Commit changes (add workflows and `poetry.lock` if needed)
  + `git push`
