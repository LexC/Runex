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
import platform
import unicodedata
 
import pandas as pd

#%% === Inicializing ===

# ---------- Support Functions ----------
def configure_logger(border: str) -> None:
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
    configure_logger(error_border)

    return {
        "valid_chars": r"_.|()[]{}-"
    }
VAR = global_variables()

#%% === Variables Manipulations ===

# ---------- Strings ----------
def str_normalize(text: str,lower=False) -> str:
    """
    Normalize a string by converting to lowercase, stripping whitespace,
    and collapsing internal whitespace to a single space.

    Args:
        text (str): The string to normalize.

    Returns:
        str: A normalized version of the input string.
    """
    if not isinstance(text, str):
        message_error(f"Not a string variable: {text}")
        return text

    # --- SETUP AND VALIDATION ---
    text = text.strip()

    # --- LOGIC ---
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('utf-8')

    if lower: text = text.lower()

    text = re.sub(rf"[^a-z0-9\s{VAR['valid_chars']}]", '', text)
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

def get_user_confirmation(question: str):
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


#%% === TO LEAVE - DIROPS ===

def path_fix(file_path: str) -> str:
    """
    Normalize and convert file paths for compatibility between Windows and Linux.

    On Linux, converts Windows-style paths (e.g., D:\\...) to /mnt/d/...
    On Windows, converts WSL paths (/mnt/d/...) to D:\\...
    Cleans special characters and redundant separators.

    Args:
        file_path (str): The file path to normalize and convert.

    Returns:
        str: A normalized and converted file path.

    Raises:
        TypeError: If the input is not a string.
    """
    if not isinstance(file_path, str):
        message_error("The path must be a string.")
        return None

    system = platform.system().lower()

    # Cleaning up
    file_path = file_path.strip()
    file_path = re.sub(r'[. ]+$', '', file_path)
    file_path = re.sub(r"[<>\"'|?*\x00-\x1F]", '', file_path)
    file_path = re.sub(r'[\\/]+', os.sep, file_path)

    if system == "linux" and re.match(r'^[a-zA-Z]:[\\/]', file_path):
        drive_letter = file_path[0].lower()
        sub_path = re.sub(r'^[a-zA-Z]:[\\/]', '', file_path)
        return f"/mnt/{drive_letter}/{sub_path}".replace('\\', '/')

    if system == "windows" and re.match(r'^/mnt/[a-z]/', file_path):
        drive_letter = file_path[5].upper()
        sub_path = file_path[7:]
        return f"{drive_letter}:\\" + sub_path.replace('/', '\\')

    return os.path.normpath(file_path)

def create_folders(path: str) -> None:
    """
    Create all directories in the given path if they do not already exist.

    Args:
        path (str): The folder path to create.

    Returns:
        None
    """
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        message_error(f"Failed to create directories for path '{path}': {e}")

#%% === Excel Utilities ===

def spreedsheet2dataframe(file_path: str, sheet_name: str = None, index_col: int = 0) -> pd.DataFrame:
    """
    Load an Excel or CSV file and convert it into a pandas DataFrame. Optionally reads
    a specific sheet from Excel files and allows customization of the index column.

    Args:
        file_path (str): Path to the Excel or CSV file.
        sheet_name (str, optional): Name of the sheet to read from Excel files.
                                    Ignored for CSV files. Defaults to None.
        index_col (int, optional): Column to set as index. Use None to keep default index.
                                   Defaults to 0.

    Returns:
        pd.DataFrame: DataFrame loaded from the file.

    Raises:
        SystemExit: If the file fails to load or is not valid.
    """
    file_path = validate_spreedsheet_path(file_path)

    try:
        if file_path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path, sheet_name=sheet_name, index_col=index_col)
        elif file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path, index_col=index_col)
    except Exception as e:
        message_exit(f"Failed to load spreadsheet file: {e}")

    return df

def validate_spreedsheet_path(file_path: str) -> bool:
    """
    Validate whether the given file path points to a valid Excel file.

    Args:
        file_path (str): Path to the file to validate.

    Returns:
        bool: True if the file exists and has a valid Excel extension, False otherwise.
    """
    ask_message = "Please enter a valid Excel file path: "
    file_path = path_fix(file_path)
    
    u=0
    while not isinstance(file_path, str):
        if u>0:message_error("The file path must be a string.")
        file_path = path_fix(request_input(ask_message))
        u+=1

    valid_extensions = (".xlsx", ".xls",".csv")

    while not (os.path.isfile(file_path) and file_path.lower().endswith(valid_extensions)):
        if not os.path.isfile(file_path):
            message_error("The file does not exist.")
        else:
            message_error("\n".join([
                "The file does not have a valid spreedsheet extension.",
                f"The valied file formats: {valid_extensions}"]))
        file_path = path_fix(request_input(ask_message))

    return file_path

def safe_append_to_excel(filename, df, sheet_name):
    """
    Writes or appends a DataFrame to an Excel file under the given sheet name.

    If the file does not exist, it creates it.
    If the file exists, it adds or replaces the specified sheet.

    Args:
        filename (str): Path to the Excel file.
        df (pd.DataFrame): DataFrame to write.
        sheet_name (str): Name of the sheet to create/replace.
    """
    
    if os.path.exists(filename):
        task = 'updated'
        # Append mode + safe sheet handling
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=True)
    else:
        task = 'created'
        # Create new file (no need for if_sheet_exists)
        with pd.ExcelWriter(filename, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=True)

    print(f"Excel {task}: {filename}")
