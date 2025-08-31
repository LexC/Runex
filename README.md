# Runex

Minimal, typed utility functions — symbols you can run.

`runex` is a small Python toolkit with two layers:
- Core ops: file and directory operations, spreadsheet loaders, typed helpers.
- Engines: higher‑level workflows, such as DirWiz for bulk directory tasks driven by a CSV plan.

Project targets Python 3.9+ and ships type hints (`py.typed`).

## Installation

- From source (recommended):
  - `git clone https://github.com/LexC/Runex.git`
  - `pip install .` (or `pip install -e .` for editable)
- Direct via pip
  - `pip install git+https://github.com/LexC/Runex.git`


Dependencies are listed in `pyproject.toml`.


## Package Layout

```
src/runex/
├── __init__.py        # Package entry + top‑level shortcut `DirWiz`
├── ops/               # Focused utilities
│   ├── __init__.py    # Public surface for ops
│   ├── dirops.py      # Directory/file operations
│   └── utils.py       # Prompts, validation, spreadsheet I/O, string tools
└── engine/
    ├── __init__.py
    └── dirwiz.py      # CSV‑driven directory workflow engine
```

## Quick Start

### Imports

```python
import runex as rx
from runex.ops import utils as rxu
from runex.ops import dirops
```

### Filesystem
```python
# Create directories (parents auto-created)
dirops.run_mkdir(["/tmp/example/a", "/tmp/example/b"])

# Copy/move with regex filters
plan = {
    1: {"source": "/data/in", "destination": "/data/out", "onlyfiles": r"\.csv$"},
    2: {"source": "/data/one.txt", "destination": "/data/out/one.txt"},
}
dirops.run_copy(plan, override=True)

# Unpack archives (zip, tar, etc.)
dirops.run_unpack([["/data/archive.zip"]])

```

### Spreadsheets
```python
# Load as DataFrame
df = rxu.load_spreadsheet("/data/table.csv", dtype="df")

# Load as dict
data = rxu.load_spreadsheet("/data/table.xlsx", tab_name="Sheet1", dtype="dict")

# Append/replace a sheet in Excel
rxu.excel_safe_append("/data/out.xlsx", "Report", df)
```

### Helpers
```python
rxu.str_normalize(" Héllo,  World!  ", lower=True)  # -> "hello, world!"
rxu.str2bool("yes")  # -> True
```

## Versioning

See `pyproject.toml` for current version. Changes are kept minimal and typed.

## License

MIT License — see `LICENSE`.


