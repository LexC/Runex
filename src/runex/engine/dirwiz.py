""" README
DirWiz is the spreadsheet-driven engine entrypoint for batch directory tasks.

Sections:
- shared configuration and prompt helpers
- spreadsheet parsing helpers
- task dispatcher and CLI entrypoint
"""

from __future__ import annotations

__all__ = [
    "determine_option",
    "determine_spreadsheet_file",
    "get_sheet_data_dircolumns",
    "get_sheet_data_sourcedestination",
    "get_sheet_data_unpack_rows",
    "get_spreadsheet_data",
    "main",
]

#%% === Libraries ===
import os
from typing import Any

# Insternal
from ..ops import ask, lprint
from ..ops import dirops as ops_dirops, tabular
from ..workflow import dirops as workflow_dirops

#%% === General Tools ===

# ---------- Variables ----------
def global_variables() -> dict[str, Any]:
    """
    Return the shared configuration used across the DirWiz engine.

    Returns:
        dict[str, Any]: Configuration values for task labels, UI formatting,
        and supported spreadsheet extensions.
    """

    return {
        "options": {
            "create_dirs": "CREATE directories",
            "copy_dirs": "COPY directories",
            "move_dirs": "MOVE directories",
            "delete_dirs": "DELETE directories",
            "decompress_files": "DECOMPRESS files",
            "decompress_all": "DECOMPRESS ALL files in directories",
        },
        "print_divider": f"\n{'-' * 50}\n",
        "supported_extensions": tuple(
            tabular.SPREADSHEET_EXTENSIONS["csv"]
            + tabular.SPREADSHEET_EXTENSIONS["excel"]
        ),
        "column_aliases": {
            "source": "source",
            "destination": "destination",
            "only": "onlyfiles",
            "onlyfile": "onlyfiles",
            "onlyfiles": "onlyfiles",
            "ignore": "ignorefiles",
            "ignorefile": "ignorefiles",
            "ignorefiles": "ignorefiles",
        },
    }


VAR = global_variables()
TASK_KEYS = tuple(VAR["options"])
DirectoryPlan = dict[int, dict[str, str | None]]
SpreadsheetTaskData = list[str] | list[list[str]] | DirectoryPlan


def _normalize_column_name(column_name: object) -> str:
    """
    Normalize spreadsheet column names for flexible matching.

    Args:
        column_name (object): Raw column label from the spreadsheet.

    Returns:
        str: Normalized lowercase column label without separators.
    """

    normalized = str(column_name).strip().lower()
    translation_table = str.maketrans("", "", " _-'\"")
    return normalized.translate(translation_table)


def _normalize_cell_value(value: object) -> str | None:
    """
    Normalize one spreadsheet cell into a trimmed string value.

    Args:
        value (object): Raw spreadsheet cell value.

    Returns:
        str | None: Cleaned string value, or ``None`` for blank cells.
    """

    if value is None:
        return None

    if isinstance(value, float) and value != value:
        return None

    cleaned_value = str(value).strip()
    return cleaned_value or None


def _load_sheet_records(spreadsheet_path: str) -> dict:
    """
    Load spreadsheet data as row records keyed by row index.

    Args:
        spreadsheet_path (str): Path to the spreadsheet file.

    Returns:
        dict: Spreadsheet rows converted into dictionaries.
    """

    sheet_records = tabular.load_spreadsheet(
        spreadsheet_path,
        dtype="dict",
        index_key=True,
        index_1thcol=False,
    )

    if not sheet_records:
        lprint.exit("The spreadsheet is empty.")

    return sheet_records


#%% === Spreadsheet Helpers ===

# ---------- Prompt Helpers ----------
def determine_spreadsheet_file(spreadsheet_path: str | None) -> str:
    """
    Return a valid spreadsheet path, prompting until one is provided.

    Args:
        spreadsheet_path (str | None): Optional spreadsheet path passed by the
            caller.

    Returns:
        str: Validated spreadsheet path.
    """

    supported_extensions = ", ".join(VAR["supported_extensions"])
    question = "Enter the full path to your spreadsheet file: "

    while True:
        if not spreadsheet_path:
            spreadsheet_path = ask.input(question).strip()

        try:
            normalized_path = ops_dirops.fix_path(spreadsheet_path)
            return ops_dirops.validate_file_path(
                normalized_path,
                supported_extensions=list(VAR["supported_extensions"]),
            )
        except FileNotFoundError:
            lprint.error("The spreadsheet file does not exist.")
        except IsADirectoryError:
            lprint.error("The provided path points to a directory.")
        except (TypeError, ValueError):
            lprint.error(
                f"Invalid file format. Supported extensions: {supported_extensions}."
            )

        spreadsheet_path = None


def determine_option(option: str | int | None) -> str:
    """
    Resolve one DirWiz task option from numeric or string input.

    Args:
        option (str | int | None): Explicit option value or ``None`` to prompt.

    Returns:
        str: Normalized task key.
    """

    if option is None:
        return ask.option(
            list(VAR["options"]),
            descriptions=list(VAR["options"].values()),
        )

    option_value = str(option).strip()
    if option_value.isdigit():
        option_index = int(option_value) - 1
        if 0 <= option_index < len(TASK_KEYS):
            return TASK_KEYS[option_index]

    if option_value in VAR["options"]:
        return option_value

    option_value_lower = option_value.lower()
    for task_key, description in VAR["options"].items():
        if option_value_lower == description.lower():
            return task_key

    lprint.exit("Invalid option.")
    raise AssertionError("unreachable")


# ---------- Sheet Data ----------
def get_spreadsheet_data(
    spreadsheet_path: str,
    task: str,
) -> SpreadsheetTaskData:
    """
    Load task-specific data from a spreadsheet plan.

    Args:
        spreadsheet_path (str): Spreadsheet file path.
        task (str): Target DirWiz task.

    Returns:
        SpreadsheetTaskData: Parsed task data formatted for the matching
        workflow function.
    """

    match task:
        case "create_dirs" | "delete_dirs" | "decompress_all":
            return get_sheet_data_dircolumns(spreadsheet_path)
        case "copy_dirs" | "move_dirs":
            return get_sheet_data_sourcedestination(spreadsheet_path)
        case "decompress_files":
            return get_sheet_data_unpack_rows(spreadsheet_path)
        case _:
            lprint.exit(f"Unsupported task: {task}")
            raise AssertionError("unreachable")


def get_sheet_data_dircolumns(spreadsheet_path: str) -> list[str]:
    """
    Read spreadsheet rows and assemble one directory path per row.

    Args:
        spreadsheet_path (str): Spreadsheet file path.

    Returns:
        list[str]: Normalized directory paths.
    """

    directory_list: list[str] = []
    sheet_records = _load_sheet_records(spreadsheet_path)

    for row in sheet_records.values():
        row_values = [
            cell_value
            for value in row.values()
            if (cell_value := _normalize_cell_value(value)) is not None
        ]

        if not row_values:
            continue

        directory_list.append(ops_dirops.fix_path(os.path.join(*row_values)))

    if not directory_list:
        lprint.exit("The spreadsheet does not contain any directory rows.")

    return directory_list


def get_sheet_data_sourcedestination(spreadsheet_path: str) -> DirectoryPlan:
    """
    Read source and destination plan rows from a spreadsheet.

    Args:
        spreadsheet_path (str): Spreadsheet file path.

    Returns:
        DirectoryPlan: Workflow plan keyed by spreadsheet row index.
    """

    directory_plan: DirectoryPlan = {}
    sheet_records = _load_sheet_records(spreadsheet_path)

    for row_index, row in sheet_records.items():
        normalized_row = {}
        for column_name, value in row.items():
            normalized_name = _normalize_column_name(column_name)
            canonical_name = VAR["column_aliases"].get(normalized_name, normalized_name)
            normalized_row[canonical_name] = _normalize_cell_value(value)

        source = normalized_row.get("source")
        destination = normalized_row.get("destination")

        if source is None and destination is None:
            continue
        if source is None or destination is None:
            lprint.exit(
                "Each populated row must include both 'source' and 'destination'."
            )

        directory_plan[row_index] = {
            "source": ops_dirops.fix_path(source),
            "destination": ops_dirops.fix_path(destination),
            "onlyfiles": normalized_row.get("onlyfiles"),
            "ignorefiles": normalized_row.get("ignorefiles"),
        }

    if not directory_plan:
        lprint.exit(
            "The spreadsheet does not contain any valid source/destination rows."
        )

    return directory_plan


def get_sheet_data_unpack_rows(spreadsheet_path: str) -> list[list[str]]:
    """
    Convert spreadsheet source/destination rows into unpack task rows.

    Args:
        spreadsheet_path (str): Spreadsheet file path.

    Returns:
        list[list[str]]: Archive rows shaped for ``workflow_dirops.run_unpack``.
    """

    unpack_rows: list[list[str]] = []
    directory_plan = get_sheet_data_sourcedestination(spreadsheet_path)

    for row in directory_plan.values():
        unpack_row = [row["source"]]
        if row["destination"]:
            unpack_row.append(row["destination"])
        unpack_rows.append(unpack_row)

    return unpack_rows


#%% === Show Time ===
def main(
    option: str | int | None = None,
    spreadsheet_path: str | None = None,
    override: bool | None = None,
) -> None:
    """
    Execute one DirWiz task driven by a spreadsheet plan.

    Args:
        option (str | int | None): Task key, numeric index, or ``None`` to
            prompt the user.
        spreadsheet_path (str | None): Optional spreadsheet file path.
        override (bool | None): Override mode forwarded to workflow functions.
    """

    print(VAR["print_divider"])

    spreadsheet_file = determine_spreadsheet_file(spreadsheet_path)
    task = determine_option(option)
    task_data = get_spreadsheet_data(spreadsheet_file, task)

    match task:
        case "create_dirs":
            ops_dirops.run_mkdir(task_data)
        case "delete_dirs":
            workflow_dirops.run_delete(task_data)
        case "copy_dirs":
            workflow_dirops.run_copy(task_data, override=override)
        case "move_dirs":
            workflow_dirops.run_move(task_data, override=override)
        case "decompress_files":
            workflow_dirops.run_unpack(task_data, override=override)
        case "decompress_all":
            workflow_dirops.run_unpack_all_in_folder(task_data, override=override)
        case _:
            lprint.exit(f"Unsupported task: {task}")

if __name__ == "__main__":
    main()
