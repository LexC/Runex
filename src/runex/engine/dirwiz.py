#%% === Libraries ===
import os

from ..ops import dirops
from ..ops import general_functions as gf

#%% === General Tools ===

# ---------- Variables ----------
def global_variables():
    """
    This function defines and returns a dictionary of key variables used in the script.

    Returns:
        dict: A dictionary containing key variables for configuration and use across the script.
    """
    VAR = {
        "options": {
            "1":{'create_dirs': "CREATE directories"},
            "2":{'copy_dirs': "COPY directories"},
            "3":{'move_dirs': "MOVE directories"},
            "4":{'delete_dirs': "DELETE directories"},
            "5":{'decompress_files': "DECOMPRESS files"},
            "6":{'decompress_all': "DECOMPRESS ALL files in directories"},
        },
        "print_div": f"\n{'-'*50}\n"
    }
    return VAR
VAR = global_variables()

#%% === spreadsheet Related ===

# ---------- Full file ----------

def determine_spreadsheet_file(ssfile):
    """
    Return a valid path for the input for the necessary spreadsheet input file.

    Args:
        ssfile (str or None): The path for the spreadsheet

    Returns:
        str
    """
    question = "Enter the full path to your spreadsheet file"

    first = True
    valid_ssfile = False
    while not valid_ssfile:

        if not ssfile or not first:
            ssfile = gf.get_user_input(question)
            first = False
        
        ssfile = dirops.fixpath(ssfile)

        if os.path.isfile(ssfile):
            if ssfile.endswith(".csv"):
                valid_ssfile = True
            else:
                gf.message_error("Invalid file format: it should be .csv")

        else: 
            gf.message_error("The file does not exist.")

    return ssfile

def determine_option(option):

    option_numbers = list(VAR["options"].keys())
    option_keys = [list(task.keys())[0] for task in VAR["options"].values()]
    option_descriptions = [list(task.values())[0] for task in VAR["options"].values()]

    option_messages = [f"\t{num}. {key}: {desc}" for num, key, desc in zip(option_numbers, option_keys, option_descriptions)]

    if not option:

        question = "\n".join(
            ["\nThese are the available tasks"] +
            option_messages +
            [f"\nEnter your choice (1-{len(VAR["options"])}): "]
        )
        option = str(input(question)).strip()

    if isinstance(option, int):
        option = str(option)
    
    if isinstance(option, str):
        
        for i,choice in enumerate(option_messages):
            if option in choice:
                return option_keys[i]
    
    gf.message_exit("Invalid Option.")

# ---------- Sheet data ----------

def get_spreadsheet_data(ssfile,task):

    """
    The spreadsheet of ssfile has a specific structure, this function will get the data of the
    sheet named task.

    Args:
        ssfile (str): The spreadsheet path 
        task (str): mkdir, del, cp, mv, unpack or unpack_all

    Returns:
        list or dict: 1 dimension array with paths for mkdir and del; or a dict where the keys are
            the row number and the values are a list, where the first value is the source, and the 
            second is the destination, for the other task. 

    """
    match task:
        case "create_dirs"      : return get_sheet_data_dircolumns(ssfile)
        case "copy_dirs"        : return get_sheet_data_sourcedestination(ssfile)
        case "move_dirs"        : return get_sheet_data_sourcedestination(ssfile)
        case "delete_dirs"      : return get_sheet_data_dircolumns(ssfile)
        case "decompress_files" : return get_sheet_data_sourcedestination(ssfile)
        case "decompress_all"   : return get_sheet_data_dircolumns(ssfile)

def get_sheet_data_dircolumns(ssfile):    
    """
    Read a CSV file and return directory paths assembled from its columns.

    Args:
        ssfile (str): The CSV file path.

    Returns:
        list: 1-dimensional array with directory paths.
    """
    sheet = gf.csv_to_dict(ssfile, indexcol=False)

    if not sheet:
        gf.exit_message("The sheet is empty.")
    else:
        dir_list = []
        for row in sheet.values():
            rowvalues = [str(x).strip() for x in row.values() if x is not None]
            dir_path = dirops.fixpath(os.path.join(*rowvalues))
            dir_list.append(dir_path)
        return dir_list

def get_sheet_data_sourcedestination(ssfile):
    """
    Read a CSV file and return source and destination pairs.

    Args:
        ssfile (str): The CSV file path.

    Returns:
        dict: A dictionary where the keys are row numbers and the values are sub-dictionaries
              containing 'source', 'destination', 'only', and 'ignore' keys.
    """
    sheet = gf.csv_to_dict(ssfile, indexcol=False)
    
    # Standardize column names
    removechars = [' ', '_', '-',"'",'"']
    standardized_sheet = {}
    for idx, row in sheet.items():
        standardized_row_1 = {k.strip().lower(): v for k, v in row.items()}
        standardized_row_2 = {}
        for item in standardized_row_1:
            for rmc in removechars:
                std_item = item.replace(rmc,"")
                standardized_row_2[std_item] = standardized_row_1[item]

        standardized_sheet[idx] = standardized_row_2

    for row in standardized_sheet.values():
        if 'source' not in row or 'destination' not in row:
            gf.exit_message("The sheet must have at least the columns: Source and Destination.")

    dir_dict = {}
    for idx, row in standardized_sheet.items():
        dir_dict[idx] = {
            "source": dirops.fixpath(row.get("source")),
            "destination": dirops.fixpath(row.get("destination")),
            "onlyfiles": row.get("onlyfiles"),
            "ignorefiles": row.get("ignorefiles")
        }

    return dir_dict


#%% === Show Time ===

def main(option = None, spreadsheet_path = None, override = None):
    """
    Main function to execute the core functionalities of the script.
    """
    print(VAR["print_div"])
    
    ssfile = determine_spreadsheet_file(spreadsheet_path)
    task = determine_option(option)

    data = get_spreadsheet_data(ssfile,task)

    match task:

        case 'create_dirs'      : dirops.run_mkdir(data)
        case 'delete_dirs'      : dirops.run_delete(data)
        case 'copy_dirs'        : dirops.run_copy(data,override=override)
        case 'move_dirs'        : dirops.run_move(data,override=override)
        case 'decompress_files' : dirops.run_unpack(data,override=override)
        case 'decompress_all'   : dirops.run_unpack_all_in_folder(data,override=override)
        case _:
            pass


if __name__ == "__main__":
    main()
    