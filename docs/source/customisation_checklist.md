# Customisation Checklist for New Projects

> 🧰 This checklist highlights places where you should replace or update names like `ek80adcp`, `ek80adcp`, or personal info like `Eleanor` to make the project your own.

Use `grep` or your editor’s search tool to find these across the project.

---

## 📁 Core Package and Import Paths

- [ ] Rename `ek80adcp/` → `your_project_name/` (*Recommended:* Don't use spaces or dashes.  Underscores are OK.)
- [ ] Update imports in all source and test files:
  - `from ek80adcp import ...`
  - `ek80adcp.tools`, `ek80adcp.readers`, etc.
- [ ] Check for relative paths in notebooks: `from ek80adcp import ...`

---

## 🧪 Testing

- [ ] In `tests/`, update:
  - Import statements: `from ek80adcp import ...`
  - File/module names like `test_ek80adcp.py`
- [ ] In `.github/actions/`, update `tests.yml`:
  - Coverage flags in `pytest`: `--cov=ek80adcp`

---

## ⚙️ Configuration and Metadata

### `pyproject.toml`
- [ ] `name = "ek80adcp-efw"` → use your PyPI-compatible name
- [ ] Update `description`, `maintainers`, and `urls`
- [ ] Edit `write_to = "ek80adcp/_version.py"`

### `.pre-commit-config.yaml`
- [ ] Edit coverage and file match patterns (e.g., `pytest --cov=...`, excludes)
- [ ] Adjust if you rename data folders or want to lint different paths

---

## 📚 Documentation

### `docs/source/conf.py`
- [ ] Change `project`, `author`, `release`
- [ ] Update copyright

### `docs/index.rst`
- [ ] Change title and subtitle lines
- [ ] Swap `ek80adcp` references
- [ ] Replace intro blurb with your own project description

### `docs/source/ek80adcp.rst`
- [ ] Update to match your new package name (or delete if auto-generated)
- [ ] Update any `automodule::` or `:mod:` references

### `docs/source/_static/logo.jpg`
- [ ] Replace with your own logo if desired

---

## 📝 Citation and License

- [ ] In `CITATION.cff`:
  - [ ] Update `title`, `authors`, `orcid`, `affiliation`
  - [ ] Insert your GitHub repo URL
  - [ ] (Later step) Add a DOI via Zenodo if desired — see `citation_guide.md`

- [ ] Review `LICENSE` to confirm you’re happy with the MIT license or swap for another

---

## 📄 Other Markdown Files

### `README.md`
- [ ] Replace:
  - `ek80adcp/*.py`
  - `Template for a Python project for oceanography`
- [ ] Customize usage examples and purpose statement
- [ ] Add badges for Zenodo or PyPI once those steps are completed

### `CONTRIBUTING.md`
- [ ] Update module paths in examples (e.g., `ek80adcp.tools`)
- [ ] Mention your GitHub handle or org instead of “Eleanor”
- [ ] Replace style file references like `ek80adcp/ek80adcp.mplstyle`

---

## 🛠 Optional Automation

### `.github/workflows/`
- [ ] In `tests.yml`, `docs.yml`, `pypi.yml`:
  - [ ] Update paths and module names
  - [ ] Adjust PyPI settings (project name, build backend, etc.)

---

> ✅ Once all these are updated, your project is cleanly decoupled from the original template and ready for public release or team collaboration.
