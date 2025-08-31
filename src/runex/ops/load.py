""" README
This script loads spreadsheet data from CSV or Excel files into a structured dictionary format.

- Organizes data using spreadsheet-style column letters (A, B, ..., AA, AB)
- Can reshape the data using any row and/or column as keys
- Automatically replaces missing or empty values with None
- Converts to a pandas DataFrame if installed
- Asks the user to correct invalid file paths or unsupported formats

Designed for users needing quick, structured access to spreadsheet content.
"""
#%% === Libraries ===

import os
import csv
from . import utils

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False

#%% === General Tools ===

# ---------- Variables ----------
def global_variables():
    """
    Defines and returns a dictionary of global variables used in the script.

    Returns:
        dict: A dictionary containing key configuration values and constants.
    """
    config = {
        "extensions": {
            "excel": [".xls", ".xlsx"],
            "csv": [".csv"]
        },
        "null_values": {"", "none", "null", "na", "n/a", "nan"}
    }
    return config
VAR = global_variables()

# ---------- Support Functions ----------

def validate_file_path(file_path: str, supported_extensions: list[str] = None) -> str:
    """
    Repeatedly prompts until a valid file path is provided. Optionally validates file extension.

    Args:
        file_path (str): Initial path to validate.
        supported_extensions (list[str], optional): List of valid extensions or a string extension.

    Returns:
        str: A validated file path.
    """
    file_path = utils.path_fix(file_path)

    while True:
        if not isinstance(file_path, str):
            utils.message_error("The path must be a string.")
        elif not os.path.exists(file_path):
            utils.message_error(f"File not found: {file_path}")
        elif not os.path.isfile(file_path):
            utils.message_error(f"Expected a file but got a directory: {file_path}")
        elif isinstance(supported_extensions, (list, str)):
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            if isinstance(supported_extensions, str):
                supported_extensions = [supported_extensions]
            if ext not in supported_extensions:
                utils.message_error(f"Unsupported file extension: {ext}")
            else:
                break
        else:
            break

        file_path = utils.path_fix(utils.request_input("Please enter a valid file path: "))

    return file_path


#%% === Spreadsheets ===

# ---------- Loaders ----------

def spreadsheet(file_path: str, tab_name: str = None, header_row: int = None, index_col: str = None, as_dataframe: bool = False) -> dict:
    """
    Reads a spreadsheet file and optionally returns the contents as a pandas DataFrame.

    Args:
        file_path (str): Path to the spreadsheet file.
        tab_name (str, optional): Sheet/tab name for Excel files.
        header_row (int, optional): Row index to use as nested dictionary keys.
        index_col (str, optional): Column letter to use as top-level dictionary keys.
        as_dataframe (bool, optional): Whether to return the result as a pandas DataFrame. Default is False.

    Returns:
        dict or pd.DataFrame: Nested dictionary or DataFrame depending on `as_dataframe`.
    """
    supported_exts = VAR["extensions"]["csv"] + VAR["extensions"]["excel"]
    file_path = validate_file_path(file_path, supported_extensions=supported_exts)
    data_dict = spreadsheet2dict(file_path, tab_name=tab_name, header_row=header_row, index_col=index_col)
    if as_dataframe:
        if not HAS_PANDAS:
            utils.message_exit("pandas is not installed. Cannot convert to DataFrame.")
        return pd.DataFrame.from_dict(data_dict, orient='index')
    return data_dict


def spreadsheet2dict(file_path: str, tab_name: str = None, header_row: int = None, index_col: str = None) -> dict:
    """
    Reads a spreadsheet file and returns its data as a nested dictionary using
    optional header row and index column.

    Args:
        file_path (str): Path to the spreadsheet file.
        tab_name (str, optional): Name of the sheet or tab to read (required for Excel files).
        header_row (int, optional): Row index to use as nested dictionary keys.
        index_col (str, optional): Column letter to use as top-level dictionary keys.

    Returns:
        dict: Nested dictionary structure based on spreadsheet content and optional formatting.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext in VAR["extensions"]["csv"]:
        raw_data = csv2dict(file_path)
    elif ext in VAR["extensions"]["excel"]:
        if not tab_name:
            utils.message_exit("tab_name must be provided for Excel files.")
        raw_data = excel2dict(file_path, tab_name)
    else:
        utils.message_exit(f"Unsupported file extension: {ext}")

    return reshape_spreadsheet_dict(raw_data, header_row=header_row, index_col=index_col)


def csv2dict(file_path: str) -> dict:
    """
    Reads a CSV file and converts it into a dictionary with column letters as keys.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        dict: Dictionary of column data keyed by spreadsheet-style column labels.
    """
    null_values = VAR["null_values"]

    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = list(csv.reader(csvfile))
        if not reader:
            return {}

        transposed = list(zip(*reader))
        return {
            index_to_column_letter(i): [
                val if str(val).strip().lower() not in null_values else None
                for val in col
            ]
            for i, col in enumerate(transposed)
        }


def excel2dict(file_path: str, tab_name: str) -> dict:
    """
    Reads an Excel sheet and converts it into a dictionary with column letters as keys.

    Args:
        file_path (str): Path to the Excel file.
        tab_name (str): Name of the sheet to read.

    Returns:
        dict: Dictionary of column data keyed by spreadsheet-style column labels.
    """
    if not HAS_PANDAS:
        utils.message_exit("pandas is required to read Excel files.")

    df = pd.read_excel(file_path, sheet_name=tab_name, dtype=object)
    return {
        index_to_column_letter(i): df.iloc[:, i].where(
            pd.notnull(df.iloc[:, i]), None
        ).tolist()
        for i in range(df.shape[1])
    }

# ---------- Support Functions ----------

def index_to_column_letter(index):
    """
    Converts a zero-based column index to spreadsheet-style letter notation.

    Args:
        index (int): Zero-based column index.

    Returns:
        str: Spreadsheet-style column label.
    """
    letters = ''
    while index >= 0:
        index, remainder = divmod(index, 26)
        letters = chr(65 + remainder) + letters
        index -= 1
    return letters


def reshape_spreadsheet_dict(flat_data: dict, header_row: int = None, index_col: str = None) -> dict:
    """
    Reshapes a flat spreadsheet-style dictionary into a nested dictionary structure
    based on an optional header row and/or index column.

    Args:
        flat_data (dict): Dictionary where keys are spreadsheet-style column labels (e.g., 'A', 'B')
                          and values are lists of cell values.
        header_row (int, optional): Row index to use for nested dictionary keys. If None, uses column letters.
        index_col (str, optional): Column letter to use as top-level keys. If None, uses 'row_{i}' as keys.

    Returns:
        dict: Nested dictionary constructed using values from header_row and/or index_col.
    """
    if header_row is None and index_col is None:
        return flat_data

    if header_row is not None and any(header_row >= len(col) for col in flat_data.values()):
        utils.message_exit("header_row index exceeds the number of rows in one or more columns.")
    if index_col is not None and index_col not in flat_data:
        utils.message_exit(f"Index column '{index_col}' not found in flat_data.")

    reshaped = {}

    row_count = len(next(iter(flat_data.values())))
    for i in range(row_count):
        outer_key = flat_data[index_col][i] if index_col else f"row_{i}"
        inner_entry = {}

        for col_label, col_values in flat_data.items():
            if i >= len(col_values):
                continue
            inner_key = col_values[header_row] if header_row is not None else col_label
            value = col_values[i]
            if inner_key is not None:
                inner_entry[inner_key] = value

        reshaped[outer_key] = inner_entry

    return reshaped
