""" README
This script reads an Excel file and loads it into a pandas DataFrame using the
first column as the index. It is structured with clearly defined sections
including variable definitions, a core function for Excel loading, and a
main execution block.
"""

#%% === Libraries ===
import os
import re
import sys
import shutil
import logging
import unicodedata

import pandas as pd

from pathlib import Path
from copy import deepcopy, copy


#-- Custom packges
from . import dirops

_IMPORTED_NAMES = set(globals().keys())
#%% === Inicializing ===

# ---------- Support Functions ----------
def _configure_logger(border: str) -> None:
    """
    Configures the root logger to format WARNING and ERROR messages
    with a visual border.

    Args:
        border (str): The border string to place above and below each log message.
    """
    class BorderedFormatter(logging.Formatter):
        def format(self, record):
            base_message = super().format(record)
            return f"{border}{record.levelname}: {base_message}{border}"

    handler = logging.StreamHandler()
    handler.setFormatter(BorderedFormatter("%(message)s"))

    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)  # Enables WARNING and ERROR logs
    logger.handlers = []  # Clear default handlers
    logger.addHandler(handler)
    logger.propagate = False

# ---------- Variables ----------
def global_variables():
    """
    Defines and returns a dictionary of global variables used in the script.

    Returns:
        dict: A dictionary containing key configuration values and constants.
    """
    error_border = "\n" + "=" * 50 + "\n"
    _configure_logger(error_border)

    config = {
        "ss_extensions": {
            "excel": [".xls", ".xlsx"],
            "csv": [".csv"]
        },
    }
    return config
VAR = global_variables()

#%% === User Interaction ===

# ---------- Messages ----------

def message_warning(message: str) -> None:
    """
    Log a formatted warning message using the configured bordered logger.

    Args:
        message (str): The warning message to log.
    """
    logging.warning(message)

def message_error(message: str) -> None:
    """
    Log a formatted error message using the configured bordered logger.

    Args:
        message (str): The error message to log.
    """
    logging.error(message)

def message_exit(message: str) -> None:
    """
    Log an error message and exit the program with status code 1.

    Args:
        message (str): The error message to log before exiting.

    Raises:
        SystemExit: Always raised to terminate the program.
    """
    message_error(f"{message}\n\nExiting the program.")
    sys.exit(1)

# ---------- User Requests ----------

def request_input(prompt_message: str) -> str:
    """
    Prompt the user for input.

    Args:
        prompt_message (str): The message displayed to the user.

    Returns:
        str: The user-provided input string.
    """
    user_input = input(prompt_message)

    return user_input

def request_confirmation(question: str):
    """
    Print a message for the user, and ask for an 'yes' or 'no' input

    Args:
        question (string)
    Returns:
        bool
    """

    while True:
        
        response = str2bool(
            request_input(f"{question} (yes/no): ").strip().lower()
            )
        
        if response is not None: return response
        else: print("Please enter 'yes' or 'no'.")

def request_option(options, descriptions: list = None, loop: bool = True) -> str:
    """
    Display a list or dictionary of options with optional descriptions and
    prompt the user to select one by number or key/string.

    Args:
        options (list | dict): A list of option strings or a dictionary with keys as
            option identifiers and values as descriptions.
        descriptions (list, optional): A list of descriptions corresponding to each
            list option, used only if `options` is a list.
        loop (bool, optional): If True, keep prompting until a valid option is
            entered. If False, prompt once and return None on invalid input.

    Returns:
        str: The selected key (from dict) or string (from list).
        None: If `loop` is False and the input is invalid.
    """
    # --- SETUP AND VALIDATION ---
    if isinstance(options, dict):
        if not options:
            message_exit("The input dictionary cannot be empty.")
        keys = list(options.keys())
        items = list(options.items())
    elif isinstance(options, list):
        if not options:
            message_exit("The input list cannot be empty.")
        keys = options
        items = list(zip(options, descriptions)) if descriptions else [(opt, "") for opt in options]
    else:
        message_exit("Options must be a list or a dictionary.")

    # --- DISPLAY OPTIONS ---
    print("Please choose from the following options:")
    for idx, (key, desc) in enumerate(items, 1):
        display = f"\t{idx}. {key}"
        if desc:
            display += f": {desc}"
        print(display)

    # --- INPUT LOOP ---
    while True:
        user_input = request_input("Select by number or name/key: ").strip()

        # Check if numeric input refers to index
        if user_input.isdigit():
            index = int(user_input) - 1
            if 0 <= index < len(keys):
                return keys[index]

        # Check if input is a direct match to a key/string
        if user_input in keys:
            return user_input

        if not loop:
            print("Invalid selection.")
            return None
        print("Invalid selection. Please try again.")

# ---------- Screens ----------

def dotted_line_fill(prefix: str, suffix: str) -> str:
    """
    Creates a string that fills the terminal width with dots between a prefix and a suffix.

    Args:
        prefix (str): The text to appear at the beginning of the line.
        suffix (str): The text to appear at the end of the line.

    Returns:
        str: A string formatted with dots filling the space between prefix and suffix.
    """

    # --- SETUP AND VALIDATION ---
    terminal_width = shutil.get_terminal_size().columns

    # --- LOGIC ---
    dots_needed = max(0, terminal_width - len(prefix) - len(suffix))
    dots = '.' * dots_needed
    result = f"{prefix}{dots}{suffix}"

    # --- RETURN ---
    return result


#%% === Variables Manipulations ===

# ---------- Strings and lists ----------

def str_normalize(text: str, lower: bool = False, valid_chars: str = "_.|()[]{}-") -> str:
    """
    Normalize a string by standardizing Unicode, cleaning unwanted characters, 
    and formatting whitespace.

    The normalization process includes:
        - Converting Unicode characters to their closest ASCII equivalent 
          (e.g., "é" → "e").
        - Optionally converting all characters to lowercase.
        - Stripping leading and trailing whitespace.
        - Collapsing multiple internal whitespace characters into a single space.
        - Removing all characters except alphanumeric and those explicitly 
          provided in `valid_chars`.

    Args:
        text (str): The string to normalize.
        lower (bool, optional): If True, convert the string to lowercase.
            Defaults to False.
        valid_chars (str, optional): String of additional characters to keep 
            (besides alphanumeric and whitespace). Defaults to "_.|()[]{}-".

    Returns:
        str: A cleaned and normalized version of the input string. If the 
        input is not a string, returns the input unchanged after logging an 
        error message.
    """
    if not isinstance(text, str):
        message_error(f"Not a string variable: {text}")
        return text

    # --- SETUP AND VALIDATION ---
    text = text.strip()

    # --- LOGIC ---
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('utf-8')

    if lower:
        text = text.lower()

    # Keep only alphanumeric, whitespace, and allowed special characters
    text = re.sub(rf"[^a-zA-Z0-9\s{re.escape(valid_chars)}]", ' ', text)
    text = re.sub(r'\s+', ' ', text)

    # --- RETURN ---
    return text

def strip_whitespaces(text):
    """
    Removes all whitespace characters from a string and returns the cleaned result.

    Args:
        text (str): The input text to process.

    Returns:
        str: The input text with all whitespace characters removed.
    """
    return re.sub(r'\s+', '', text)

def str2float(number_str):
    """
    Converts a number string with commas into a float. If a numeric type is
    provided instead of a string, it is returned as a float. Returns None
    for unsupported types or invalid inputs.

    Args:
        number_str (str | int | float | complex): A number or string representing
            a number that may include commas (e.g., '2,382').

    Returns:
        float | None: Parsed float value, or None if the input is invalid.
    
    Raises:
        ValueError: If the string is not a valid float after removing commas.
    """
    
    if isinstance(number_str, str):
        cleaned = number_str.strip().replace(',', '')
        return float(cleaned)
    elif isinstance(number_str, (int, float, complex)):
        return float(number_str)

def str2bool(value):
    """
    Convert a string input to a boolean value or None.

    Args:
        value (str): The input string to convert.

    Returns:
        bool or None: The converted boolean value, or None if input is unrecognized.
    """

    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    if value in {'true', 'yes', '1', 'y'}:
        return True
    elif value in {'false', 'no', '0', 'n'}:
        return False
    return None

def match_terms_to_text(
        text: str, search_terms: list, normalize: bool = True,
        valid_chars: str = ".&+#%$€£"
        ) -> bool:
    """
    Check if any word or phrase from a given list is present in the text, 
    with optional normalization.

    When `normalize` is True, both the text and search terms are processed 
    using `str_normalize`. See `str_normalize` for details on how 
    normalization is performed.

    Args:
        text (str): The input text to search within.
        search_terms (list): List of words or phrases to check for in the text.
        normalize (bool, optional): Whether to normalize text and terms before 
            matching. Defaults to True.
        valid_chars (str, optional): Additional characters to keep during 
            normalization. Only applies if `normalize=True`. 
            Defaults to ".&-+#%$€£".

    Returns:
        bool: True if any word or phrase from `search_terms` is found in `text`,
        otherwise False.
    """
    # --- SETUP AND VALIDATION ---
    if not isinstance(text, str) or not isinstance(search_terms, list):
        return False

    if normalize:
        # Normalize input text and search terms
        normalized_text = str_normalize(text, lower=True, valid_chars=valid_chars)
        normalized_terms = [
            str_normalize(term, lower=True, valid_chars=valid_chars) 
            for term in search_terms
        ]
    else:
        normalized_text = text
        normalized_terms = search_terms

    # --- LOGIC ---
    for term in normalized_terms:
        escaped_pattern = re.escape(term)

        if " " in term:
            # Match phrase directly
            if re.search(escaped_pattern, normalized_text):
                return True
        else:
            # Match whole word only
            if re.search(rf"\b{escaped_pattern}\b", normalized_text):
                return True

    # --- RETURN ---
    return False






# -----> Validations

def validate_string(value: str, allowed_options: list[str], case_sensitive: bool = False) -> str:
    """
    Validates whether a string matches one of the allowed options. Prompts until valid.

    Args:
        value (str): The input string to validate.
        allowed_options (list[str]): A list of acceptable string values.
        case_sensitive (bool): Whether comparison is case-sensitive. Default is False.

    Returns:
        str: A validated string from the allowed options.
    """
    if not isinstance(allowed_options, list) or not all(isinstance(opt, str) for opt in allowed_options):
        message_exit("allowed_options must be a list of strings.")

    val_to_check = value if case_sensitive else value.lower()
    options = allowed_options if case_sensitive else [opt.lower() for opt in allowed_options]

    if val_to_check not in options:
        message_exit(f"Invalid option: {value}.\nAllowed options are: {', '.join(allowed_options)}")

# ---------- Dictionaries ----------

def lowercase_keys_in_dict(target_dict: dict, keys_to_lowercase: list) -> None:
    """
    Converts specific keys inside nested dictionaries of a main dictionary to lowercase.

    Args:
        target_dict (dict): The outer dictionary whose inner dictionaries will be processed.
        keys_to_lowercase (list): List of target key names to match (case-insensitive) and convert to lowercase.

    """
    for inner_dict in target_dict.values():
        keys_to_fix = [key for key in inner_dict.keys() if key.lower() in keys_to_lowercase]
        for key in keys_to_fix:
            lower_key = key.lower()
            if lower_key != key:
                inner_dict[lower_key] = inner_dict.pop(key)


#%% === Loaders and Outputs===

# ---------- Spreadsheets ----------

def load_spreadsheet(file_path: str, tab_name: str = None,
        header_1throw: bool = True, index_1thcol: bool = False, index_key: bool = False,
        dtype: str = "df", **kwargs):
    """
    Reads a spreadsheet file (CSV or Excel) and returns its content as either a
    pandas DataFrame or a nested dictionary with flexible indexing and headers.

    Args:
        file_path (str): Path to the spreadsheet file.
        tab_name (str, optional): Sheet name for Excel files.
        header_first_row (bool): If True, uses the first row as headers.
        index_first_col (bool): If True, uses the first column as index.
        use_index_as_key (bool): If True and dtype is 'dict', orients dictionary by row index.
        dtype (str): Output format; "df" for DataFrame, "dict" for dictionary.

    Returns:
        dict or pd.DataFrame: Parsed content in the specified output format.
    """
    
    # --- SETUP AND VALIDATION ---

    dtype_options = ["df","dict"]

    ext_csv = VAR["ss_extensions"]["csv"]
    ext_exc = VAR["ss_extensions"]["excel"]
    supported_exts = ext_csv + ext_exc

    header = 0 if header_1throw else None
    index_col = 0 if index_1thcol else False
    orient = 'index' if index_key else 'dict'

    validate_string(dtype,dtype_options)

    validated_path  = dirops.validate_file_path(file_path, supported_extensions=supported_exts)
    
    suffix = Path(validated_path).suffix

    # --- LOGIC ---
    if suffix in ext_csv:
        df = pd.read_csv(
            validated_path,
            header=header, index_col=index_col, 
            **kwargs)
    elif suffix in ext_exc:
        df = pd.read_excel(
            validated_path, sheet_name=tab_name,
            header=header, index_col=index_col, 
            **kwargs)

    # --- RETURN ---
    match dtype:
        case "df":
            return df
        case "dict":
            return df.to_dict(orient=orient)
        case _:
            message_exit("")

# ---------- Loaders ----------

def excel_safe_append(file_path: str, sheet_name: str, data_frame: pd.DataFrame) -> None:
    """
    Writes or appends a DataFrame to an Excel file with a specified sheet name.

    If the file exists, it updates or replaces the given sheet.
    If the file does not exist, it creates a new Excel file.

    Args:
        file_path (str): Path to the Excel file to create or update.
        sheet_name (str): Name of the sheet to create or replace in the Excel file.
        data_frame (pd.DataFrame): DataFrame to write to the Excel sheet.
    """
    file_exists = os.path.exists(file_path)
    write_mode = 'a' if file_exists else 'w'
    sheet_settings = {'if_sheet_exists': 'replace'} if file_exists else {}

    with pd.ExcelWriter(file_path, engine='openpyxl', mode=write_mode, **sheet_settings) as writer:
        data_frame.to_excel(writer, sheet_name=sheet_name, index=True)

    print(f"Excel {'updated' if file_exists else 'created'}: {file_path}")


#%% === Closing ===

# --- build the public API: only functions/classes defined here ---
def _build_public():
    import inspect
    defined_after = set(globals().keys()) - _IMPORTED_NAMES
    out = []
    for name in defined_after:
        if name == "__all__" or name.startswith("_"):
            continue
        obj = globals()[name]
        # only code you wrote: functions/classes (no modules, no constants)
        if inspect.isfunction(obj) or inspect.isclass(obj):
            # ensure it’s defined in THIS module, not re-imported
            if getattr(obj, "__module__", __name__) == __name__:
                out.append(name)
    return sorted(out)

__all__ = _build_public()

# Make dir(module) show only the public surface
def __dir__(): return sorted(__all__)

# tidy up internals
del _build_public, _IMPORTED_NAMES
