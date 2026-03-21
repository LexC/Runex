""" README
Tabular file helpers for the ops layer.

Sections:
- lazy spreadsheet dependency loading
- readers for CSV and Excel inputs
- safe Excel write helpers
"""

from __future__ import annotations

__all__ = ["SPREADSHEET_EXTENSIONS", "excel_safe_append", "load_spreadsheet"]

#%% === Libraries ===
import os

from typing import TYPE_CHECKING, Any
from pathlib import Path

if TYPE_CHECKING:
    import pandas as pd

# Insternal
from . import common, dirops

#%% === General Tools ===

# ---------- Variables ----------
def global_variables() -> dict[str, dict[str, list[str]]]:
    """
    Return shared spreadsheet configuration values.

    Returns:
        dict[str, dict[str, list[str]]]: Supported spreadsheet extensions.
    """

    return {
        "spreadsheet_extensions": {
            "excel": [".xls", ".xlsx"],
            "csv": [".csv"],
        }
    }


VAR = global_variables()
SPREADSHEET_EXTENSIONS = VAR["spreadsheet_extensions"]


def _import_pandas():
    """Import pandas only when spreadsheet features are used."""

    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "pandas is required for spreadsheet operations. "
            "Install the spreadsheet extras with `pip install 'runex[spreadsheets]'` "
            "or `pip install '.[spreadsheets]'`."
        ) from exc

    return pd


def _resolve_load_settings(
    header_1throw: bool,
    index_1thcol: bool,
    index_key: bool,
    kwargs: dict[str, Any],
) -> tuple[list[str], list[str], int | bool, int | None, str]:
    """
    Resolve extensions and pandas keyword defaults for spreadsheet loading.

    Args:
        header_1throw (bool): Whether the first row should be treated as the
            header.
        index_1thcol (bool): Whether the first column should be used as the
            DataFrame index.
        index_key (bool): Whether ``dict`` output should use index orientation.
        kwargs (dict[str, Any]): Additional pandas keyword arguments.

    Returns:
        tuple[list[str], list[str], int | bool, int | None, str]: CSV
        extensions, Excel extensions, index column setting, header setting,
        and dict orientation.
    """

    csv_extensions = SPREADSHEET_EXTENSIONS["csv"]
    excel_extensions = SPREADSHEET_EXTENSIONS["excel"]
    index_col = kwargs.pop("index_col", 0 if index_1thcol else False)
    header = kwargs.pop("header", 0 if header_1throw else None)
    orient = kwargs.pop("orient", "index" if index_key else "dict")
    return csv_extensions, excel_extensions, index_col, header, orient


#%% === Tabular Helpers ===
def load_spreadsheet(
    file_path: str,
    tab_name: str | None = None,
    header_1throw: bool = True,
    index_1thcol: bool = False,
    index_key: bool = False,
    dtype: str = "df",
    **kwargs,
) -> pd.DataFrame | dict:
    """
    Read a CSV or Excel file into a DataFrame or nested dictionary.

    Args:
        file_path (str): Spreadsheet path.
        tab_name (str | None): Excel sheet name when reading Excel files.
        header_1throw (bool): Whether the first row is the header row.
        index_1thcol (bool): Whether the first column should become the index.
        index_key (bool): Whether dict output should be oriented by index.
        dtype (str): Output format, either ``"df"`` or ``"dict"``.
        **kwargs: Extra arguments forwarded to pandas readers.

    Returns:
        pd.DataFrame | dict: Loaded spreadsheet data.
    """

    common.validate_string(dtype, ["df", "dict"])

    csv_extensions, excel_extensions, index_col, header, orient = (
        _resolve_load_settings(
            header_1throw=header_1throw,
            index_1thcol=index_1thcol,
            index_key=index_key,
            kwargs=kwargs,
        )
    )

    validated_path = dirops.validate_file_path(
        file_path,
        supported_extensions=csv_extensions + excel_extensions,
    )
    suffix = Path(validated_path).suffix.lower()
    pd = _import_pandas()

    if suffix in csv_extensions:
        data_frame = pd.read_csv(
            validated_path,
            header=header,
            index_col=index_col,
            **kwargs,
        )
    elif suffix in excel_extensions:
        data_frame = pd.read_excel(
            validated_path,
            sheet_name=0 if tab_name is None else tab_name,
            header=header,
            index_col=index_col,
            **kwargs,
        )
    else:
        raise ValueError(f"Unsupported spreadsheet extension: {suffix}")

    if dtype == "df":
        return data_frame

    return data_frame.to_dict(orient=orient)


def excel_safe_append(
    file_path: str,
    sheet_name: str,
    data_frame: pd.DataFrame,
) -> None:
    """
    Create or update an Excel sheet with a DataFrame.

    Args:
        file_path (str): Destination Excel workbook path.
        sheet_name (str): Target sheet name.
        data_frame (pd.DataFrame): Data to write into the sheet.
    """

    pd = _import_pandas()
    file_exists = os.path.exists(file_path)
    write_mode = "a" if file_exists else "w"
    sheet_settings = {"if_sheet_exists": "replace"} if file_exists else {}

    with pd.ExcelWriter(
        file_path,
        engine="openpyxl",
        mode=write_mode,
        **sheet_settings,
    ) as writer:
        data_frame.to_excel(writer, sheet_name=sheet_name, index=True)
