# Runex

Minimal, typed utility functions — symbols you can run.

`runex` is a small Python toolkit with three layers:
- Core ops: low-level file and directory operations, spreadsheet loaders, typed helpers.
- Workflows: composed, reusable library tasks built on top of ops.
- Engines: CLI entrypoints such as DirWiz for bulk directory tasks driven by a spreadsheet plan.

Project targets Python 3.9+.
Spreadsheet support is optional via the `spreadsheets` extra.

## Installation

- From source (recommended):
  - `git clone https://github.com/LexC/Runex.git`
  - `pip install .` for the core library
  - `pip install '.[spreadsheets]'` for spreadsheet support
  - `pip install -e .` (or `pip install -e '.[spreadsheets]'`) for editable installs
- Direct via pip
  - `pip install git+https://github.com/LexC/Runex.git`
  - `pip install "runex[spreadsheets] @ git+https://github.com/LexC/Runex.git"`


Optional dependencies are listed in `pyproject.toml`.


## Package Layout

```
src/runex/
├── __init__.py        # Package entry + top‑level shortcut `DirWiz`
├── ops/               # Focused utilities
│   ├── __init__.py    # Public surface for ops
│   ├── common.py      # String, validation, and small data helpers
│   ├── dirops.py      # Low-level path and filesystem operations
│   ├── lprint.py      # Console output helpers
│   └── tabular.py     # Tabular file loading/writing helpers
├── workflow/          # Composed library workflows
│   ├── __init__.py
│   └── dirops.py      # Batch filesystem workflows
└── engine/
    ├── __init__.py
    └── dirwiz.py      # Spreadsheet-driven directory workflow engine
```

## Quick Start

### Imports

```python
import runex as rx
from runex.ops import dirops as ops_dirops
from runex.ops import common as ops_common
from runex.ops import tabular as ops_tabular
from runex.workflow import dirops as wf_dirops
```

### Filesystem
```python
# Create directories (parents auto-created)
ops_dirops.run_mkdir(["/tmp/example/a", "/tmp/example/b"])

# Normalize a path for the current host OS
clean_path = ops_dirops.fix_path(r"C:\data\in")

# Build a workflow plan dictionary
plan = ops_dirops.make_dir_dict("/data/in", "/data/out", onlyfiles=r"\.csv$")
```

### Workflows
```python
wf_dirops.run_copy(plan, override=True)
wf_dirops.run_delete(["/tmp/example/a", "/tmp/example/b"], skip_confirmation=True)
wf_dirops.run_unpack_all_in_folder(["/data/incoming"], recursive=True)
```

### Tabular Files
```python
# Load as DataFrame
df = ops_tabular.load_spreadsheet("/data/table.csv", dtype="df")

# Load as dict
data = ops_tabular.load_spreadsheet(
    "/data/table.xlsx",
    tab_name="Sheet1",
    dtype="dict",
)

# Append/replace a sheet in Excel
ops_tabular.excel_safe_append("/data/out.xlsx", "Report", df)
```

Install note: spreadsheet features require the `spreadsheets` extra.

### Helpers
```python
ops_common.str_normalize(" Héllo World ", lower=True)  # -> "hello world"
ops_common.str2bool("yes")  # -> True
```

## Versioning

Documentation note: this codebase is being treated as version `1.0.0`.
Changes are kept minimal and typed.

## License

MIT License — see `LICENSE`.
