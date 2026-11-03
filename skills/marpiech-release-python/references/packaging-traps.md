# Packaging traps (setuptools, hatch, poetry, flit)

Read when the audit shows unwanted, missing or unexpected files, or before changing
packaging configuration.

## What ships

- **The wheel and the sdist are different file sets.** The sdist usually adds README,
  CHANGELOG, LICENSE, `PKG-INFO`, build config — and with some backends everything
  tracked in git. Audit both.
- **README is the project page on the index**, and the long description is embedded in
  the metadata of every artifact. Anything in it is published.
- **Tests inside the package directory ship** unless excluded (`find_packages(exclude=…)`,
  `[tool.setuptools.packages.find] exclude`, hatch `exclude`). Tests outside it can still
  land in the sdist.
- **setuptools `package_data` globs are per directory level**, not recursive; patterns
  may contain separators (`models/*/*.yml`). Verify in the built wheel, not in config.
- **A data-only directory** needs no `__init__.py`; adding it to the package list
  without `package_data` (or the reverse) silently drops the data from the wheel.
- **`include_package_data=True` + `MANIFEST.in`** controls the sdist and, for
  setuptools, data inside packages — a file missing from `MANIFEST.in` may be in the
  wheel built from the tree but missing from a wheel built from the sdist (which is what
  `python -m build` does by default).
- **Symlinks** inside the package are resolved or dropped depending on the backend;
  do not rely on them.

## Versions

- **Several declarations must agree** (pyproject, setup.py, `__init__.__version__`, a
  `version.py`). Prefer a single source (`dynamic = ["version"]` with
  `attr:` / hatch `version.path`, or setuptools_scm).
- **Generated version files** (headers like "generated from setup.py") are regenerated,
  not edited by hand.
- Versions are compared by PEP 440, not as strings: `1.10.0 > 1.9.0`; `1.4.0rc1 < 1.4.0`.

## Compatibility

- **Syntax and stdlib of the oldest supported Python** (e.g. no walrus on 3.7, no
  `match` before 3.10, no `str.removeprefix` before 3.9, no `argparse.BooleanOptionalAction`
  before 3.9). `ast.parse(..., feature_version=(3, X))` catches syntax only; run the tests
  on that interpreter.
- **Dependencies that publish only sdists** compile on install: a clean machine without
  a compiler fails. Check dependencies for wheels on the oldest Python and common
  platforms, or prefer alternatives that ship wheels.
- `requires-python` must be set — without it, old interpreters install a release they
  cannot run.

## Clean-install gate

```bash
# container (preferred): nothing from the repo except the wheel
docker run --rm -v "$PWD/dist:/dist:ro" python:<oldest>-slim sh -c '
  pip install --no-cache-dir /dist/*.whl &&
  python -c "import <pkg>, sys; print(<pkg>.__version__)" &&
  <cli> --help >/dev/null && echo CLEAN-INSTALL-OK'

# venv fallback (only if <oldest> is installed locally)
d=$(mktemp -d) && python<oldest> -m venv "$d/v" && "$d/v/bin/pip" install dist/*.whl \
  && (cd "$d" && "$d/v/bin/python" -c "import <pkg>") ; rm -rf "$d"
```

Run the import from a directory **outside** the repository — inside it, Python imports
the source tree instead of the installed wheel and hides missing files.

When a container build needs a build context, use an allow-list `.dockerignore` (`*`,
then `!` entries for what the build needs): a deny-list goes stale the first time
someone drops a large dataset into the repository, and the context balloons.

## After publishing

- A version cannot be re-uploaded or re-used, even after deletion. Fix forward with a new
  version; **yank** a harmful one (unpinned installs skip it, pinned installs still get it).
