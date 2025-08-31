""" README
This file contains the core directory opetarions functions
"""
#%% === Libraries ===
import os
import re
import stat
import shutil
import pathlib

from . import utils

#%% === Dirs Manipulation ===

# ---------- Public ----------

def run_mkdir(dir_list):
    """
    Creates one or more directories, including any necessary parent directories.

    Args:
        dir_list (str or list): A directory path or a list of directory paths to create.

    Raises:
        SystemExit: If the input is not a string or a list of strings (handled by _check_input_str_list).
        OSError: If the directory cannot be created due to permission issues or invalid paths.
    """

    dir_list = _check_input_str_list(dir_list)
    for dir in dir_list:
        os.makedirs(dir, exist_ok=True)

def run_delete(dir_list:list,skip_confimation=False):
    """
    Deletes directories, including non-empty directories

    Args:
        dir_list (list): a list with directories
    """
    question = f"Are you sure you want to Permanently Delete the selected the following directories:\n{'\n'.join(dir_list)}\n"
    confirmation = skip_confimation if skip_confimation else utils.get_user_confirmation(question)

    if confirmation:    
        for dir in dir_list:

            shutil.rmtree(dir,onexc = _remove_readonly)

def run_copy(dir_dict:dict,override:bool = None):
    _run_copy_or_move('cp', dir_dict, override)

def run_move(dir_dict:dict,override:bool = None):
    _run_copy_or_move('mv', dir_dict,override)

def run_rename(dir_dict:dict):
    """
    Renames directories based on a dictionary containing source and destination paths.

    Args:
        dir_dict (dict): Nested dictionary where each item contains 'source', 'destination'
    """
    for item in dir_dict.values():
        src, dst, _, _ = _get_directory_info(item)
    
        if _check_valid_dir(src):
            os.rename(src,dst)

def run_unpack(dir_list:list,override:bool = None, another_unpack:int = None):
    """
    This function will unpack compressed files.

    Args:
        dir_list (list): Each element of list is a list with one of the following
            2 elements: source path and destinatination path
            1 element: source path
                In this case, the destination will be the source path withou file extention
    """
    
    if override == None:
        override = utils.get_user_confirmation("Do you want to overwrite existing files?")

    for row in dir_list:
        
        src = row[0]
        valid_format, extention = _check_valid_unpack(src)

        if len(row) == 2: dst = row[1]
        elif len(row) == 1: dst = src.removesuffix(extention)
        
        if valid_format:
            if override or not os.path.isdir(dst):
                _unpack_func(src,dst)

def run_unpack_all_in_folder(dir_list, recursive=False,override=False):
    
    if override == None:
        override = utils.get_user_confirmation("Do you want to overwrite existing files?")

    for i,src in enumerate(dir_list):
        message = "\n   ".join([f"{utils.VAR['print_tast_div']}Task {i+1}/{len(dir_list)}",src,""]) 
        print(message)

        count = 0
        
        unpacked_dirs = []
        if recursive:
            files_unpacked = True
            while files_unpacked:   
                files_unpacked = False

                for dirpath, _, filenames in os.walk(src):
                    for filename in filenames:
                        
                        file_path = os.path.join(dirpath,filename)
                        valid_format,_ = _check_valid_unpack(file_path,silent=True)
                        
                        if valid_format and file_path not in unpacked_dirs:
                            
                            count+=1
                            message = f"Unpacking {count:02}:\t{file_path}"
                            print(message)

                            run_unpack([[file_path]],override=override,another_unpack=1)
                            print("|-> DONE\n")
                            unpacked_dirs.append(file_path)
                            files_unpacked = True
        
        else:
            for dirpath, _, filenames in os.walk(src):
                for filename in filenames:
                    
                    file_path = os.path.join(dirpath,filename)
                    valid_format,_ = _check_valid_unpack(file_path,silent=True)
                    
                    if valid_format and file_path not in unpacked_dirs:
                        
                        count+=1
                        message = f"Unpacking {count:02}:\t{file_path}"
                        print(message)

                        run_unpack([[file_path]],override=override,another_unpack=1)
                        unpacked_dirs.append(file_path)

# ---------- Private ----------

def _run_copy_or_move(option:str, dir_dict:dict,override:bool = None):
    """
    Copies or moves files from source directories to destination directories, 
    based on user selection, while handling overwrite behavior. Empty folders 
    are neither moved nor copied.

    Args:
        option (str): 'cp' to copy files, 'mv' to move files.
        dir_dict (dict): Dictionary where each value is a dict containing 
            'source' and 'destination' paths, and optionally 'onlyfiles' and 'ignorefiles' regex patterns.
        override (bool, optional): If True, overwrite existing files without prompting. 
            If False, skip existing files. If None, prompts the user.
    """
    
    # Confirming to the user
    if override == None:
        override = utils.get_user_confirmation("Do you want to overwrite existing files?")
    elif type(override) != bool:
        utils.message_error('The override option must be a boolian')
        override = utils.get_user_confirmation("Do you want to overwrite existing files?")


    for index, item in enumerate(dir_dict.values()):
        
        src, dst, onlf, ignf = _get_directory_info(item)
        # Print to the user
        m1 = f"- Only the files that matches the RegEx: {onlf}" if onlf else ""
        m2 = f"- Ignoring the files that matches the RegEx: {ignf}" if ignf else ""
        message = [
            f"\n{'-'*5}\nTask {index+1}/{len(dir_dict)}",
            f"Copping {m1}{m2}" if option == "cp" else f"Moving {m1}{m2}",
            f"\t{src}",
            "to",
            f"\t{dst}\n"
        ]
        message = "\n\t".join(message)
        print(message)
        
        # LOGIC
        if _check_valid_dir(src) and _check_not_infloop(src,dst):
            
            if os.path.isdir(src):
                for root, _, files in os.walk(src):
                    
                    if not onlf and not ignf:
                        rel_root = os.path.relpath(root, src)
                        dst_root = os.path.join(dst, rel_root)
                        os.makedirs(dst_root, exist_ok=True)


                    for file in files:

                        rel_path = os.path.relpath(os.path.join(root, file), src)
                        
                        if onlf and not re.search(onlf, file):
                            continue
                        if ignf and re.search(ignf, file):
                            continue

                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(dst, rel_path)
                        
                        if override:
                            _copy_or_move(option, src_path, dst_path)
                        else:
                            if not os.path.exists(dst_path): _copy_or_move(option, src_path, dst_path)
        
            elif os.path.isfile(src):
                
                if not os.path.isfile(dst) or override:
                    _copy_or_move(option, src, dst)

def _copy_or_move(option:str, src:str, dst:str):
    """
    This function will execute the copy or move function.

    Args:
        option (str): 'cp' to execute the copy function, 'mv' for the move function
        src (str): The path for the source directory
        dst (str): The path for the destination directory
    """
    match option:
        case "cp":
            if os.path.isdir(src):
                shutil.copytree(src,dst,dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        
        case "mv": shutil.move(src, dst)

def _unpack_func(src,dst):
    
    try:
        shutil.unpack_archive(src,dst)
    except:
        message = f"Unable to unpack\n{' '*5}{src}\nSkiping Task"
        utils.message_error(message)

def _get_directory_info(item: dict) -> tuple:
    """
    Extracts the 'source', 'destination', 'onlyfiles', and 'ignorefiles' fields from a dictionary.

    Args:
        item (dict): Dictionary containing at least 'source' and 'destination', and optionally 'onlyfiles' and 'ignorefiles'.

    Returns:
        tuple: A tuple containing (source, destination, onlyfiles, ignorefiles) values. If 'onlyfiles' or 'ignorefiles' are missing, they are returned as None.

    Raises:
        KeyError: If 'source' or 'destination' are missing from the input dictionary.
    """
    src = item.get('source')
    dst = item.get('destination')
    onlf = item.get('onlyfiles', None)
    ignf = item.get('ignorefiles', None)

    if src is None or dst is None:
        message = "Each line of the file must contain 'source' and 'destination' values."
        utils.message_exit(message)

    return src, dst, onlf, ignf 

#%% === Directory Tools ===

def locate_files_by_extension(folder_path, extension):
    """
    Find all files in a directory that match a given file extension.

    Args:
        folder_path (str or Path): The path to the folder where files should be searched.
        extension (str): The file extension to match (e.g., 'csv', 'txt').

    Returns:
        list[pathlib.Path]: A list of Path objects matching the given extension.
    """
    folder = pathlib.Path(folder_path)
    files = list(folder.glob(f'*.{extension}'))
    return files

def locate_files_by_name_pattern(folder_path, filename):
    """
    Find all files in a directory that contain a specific filename pattern.

    Args:
        folder_path (str or Path): The path to the folder where files should be searched.
        filename (str): The filename pattern to search for (can be partial).

    Returns:
        list[pathlib.Path]: A list of Path objects matching the filename pattern.
    """
    folder = pathlib.Path(folder_path)
    files = list(folder.glob(f'*{filename}*'))
    return files

    
#%% === Support ===

# ---------- Public ----------

def fixpath(path:str):
    """
    Make the path compatible with the operating system and correct common path definition errors.

    Args:
        path (str): The path can be for windows, linux, mac or to a server (inside windows).

    Returns:
        str
    """
    
    if os.name == "nt":
        windows_remove_chars = '<>"|?'
        for wrc in windows_remove_chars:
            path = path.replace(wrc,"")

    if path.startswith("\\\\"):
        prefix = "\\\\"
    elif path.startswith("/"):
        prefix = "/"
    else:
        prefix = ""
    
    cleaned = re.sub(r"[\\/]+", "/", path.lstrip("\\"))
    normalized = os.path.join(*cleaned.split("/"))

    if ":" in normalized and ":\\" not in normalized:
        normalized = normalized.replace(":",":\\")
    
    return f"{prefix}{normalized}"

def get_parent_folder_by_level(path, level):
    """
    Gets the name of the parent folder at a specified level from a file path.
    
    Args:
        path (str): The full file path.
        level (int): The level of the parent folder to retrieve. 
                     1 = immediate parent, 2 = grandparent, etc.
    
    Returns:
        str: Name of the folder at the specified parent level, or 'ROOT' if not enough levels.

    """
    path = fixpath(path)
    parts = os.path.normpath(path).split(os.sep)

    if len(parts) >= level + 1:
        return parts[-(level + 1)]
    else:
        utils.message_error("Parent not found")

def find_files_by_regex(base_path, file_pattern, recursive=True):
    """
    Returns a list of file paths under a base directory that match a given regex pattern.

    Args:
        base_path (str): Directory path to search in.
        pattern (str): Regular expression to match filenames.
        recursive (bool): If True, search subdirectories recursively.

    Returns:
        list[str]: List of matching file paths.

    Raises:
        re.error: If the regex pattern is invalid.
        OSError: If the directory path is inaccessible.
    """
    file_regex = re.compile(file_pattern)
    matched_files = []

    if recursive:
        for root, _, files in os.walk(base_path):
            for file in files:
                if file_regex.match(file):
                    file_path = os.path.join(root, file)
                    matched_files.extend(file_path)
    else:
        for f in os.listdir(base_path):
            full_path = os.path.join(base_path, f)
            if os.path.isfile(full_path) and file_regex.match(f):
                matched_files.append(full_path)

    return matched_files

def make_dir_dict(source,destination,onlyfiles=None, ignorefiles = None):
    """
    Creates a dictionary mapping source directories to destination directories,
    along with optional filters for inclusion and exclusion.

    Args:
        source (str or list): Source directory path(s).
        destination (str or list): Destination directory path(s).
        onlyfiles (optional, str or list): RegEx to include. Defaults to None.
        ignorefiles (optional, str or list): RegEx to exclude. Defaults to None.

    Returns:
        dict: A dictionary where each key maps to a set of directory parameters.

    """
    # --- SETUP AND VALIDATION ---
    tonlyfiles = type(onlyfiles) if onlyfiles else type(destination)
    tignorefiles = type(ignorefiles) if ignorefiles else type(destination)
    
    if not(isinstance(source,(str,list)) and type(source)==type(destination)==tonlyfiles==tignorefiles):
        utils.message_exit("The types of the input variable don't match")
    
    # --- LOGIC ---
    if isinstance(source,str):
        return {0:{
            'source': source,
            'destination': destination,
            'onlyfiles': onlyfiles,
            'ignorefiles': ignorefiles
        }}
    
    dir_dict = {}
    if not onlyfiles: onlyfiles = [None for _ in source]
    if not ignorefiles: ignorefiles = [None for _ in source]
    for i,(src, dst, onlf, ignf) in enumerate(zip(source,destination,onlyfiles, ignorefiles)):
        dir_dict[i] =  {
            'source': src,
            'destination': dst,
            'onlyfiles': onlf,
            'ignorefiles': ignf
        }
    return dir_dict

# ---------- Private ----------

def _add_path_sufix(dst):
    sufix = 1
    new_dst = str(dst)
    while True:
        if not os.path.exists(new_dst):
            return new_dst
        else:
            new_dst = f"{dst}_{str(sufix)}"
            sufix+=1

def _check_not_infloop(src:str,dst:str):
    """
    Checks if directory dst is contained in the directory src, which can cause an infinit loop in
    other functions.

    Args:
        src (str): The path for the source directory
        dst (str): The path for the destination directory

    Returns:
        bool
    """
    src_base, src_last = os.path.split(src)
    dst_base, dst_last = os.path.split(dst)

    if os.path.isdir(src) and dst in src and src_base!=dst_base:
        utils.message_error(f"Possible infinite loop in \n{src}\n{dst}\nSkiping Task")
        return False
    else:
        return True

def _check_valid_dir(dir_path:str,exit_process = False):
    """
    Checks if directory exists

    Args:
        dir_path (sir): a directory path

    Returns:
        bool
    """
    if os.path.exists(dir_path):
        return True
    else:
        message = f"Diretory not found.\n{dir_path}"
        if exit_process:
            utils.message_exit(message)
        else:
            utils.message_error(f"{message}\nSkiping Task")
            return False

def _check_valid_unpack(dir_path:str,silent=False):
    """
    Checks if directory extention is supported for further processing

    Args:
        dir_path (sir): a directory path

    Returns:
        bool
    """
    packformat = ""
    valid_format = False
    dir_exists = os.path.exists(dir_path)
    if dir_exists:
        unp_formats = shutil.get_unpack_formats()
        supported_formats = []
        for row in unp_formats:
            for extention in row[1]:
                supported_formats.append(extention)
                if dir_path.endswith(extention):
                    valid_format = True
                    packformat = extention
    
    if not silent:
        if not dir_exists:
            utils.message_error(f"Directory do not exists.\n{dir_path}\nSkiping Task...")
        if not valid_format:
            utils.message_error(
            f"""Format not supported.
            {dir_path}\n
            The supported formats are: {", ".join(supported_formats)}
            Skiping Task..."""
            )
    
    return (valid_format,packformat)

def _remove_readonly(func,path:str,_):
    """
    Removes the read-only attribute from a file and applies a given function to it.

    Args:
        func (callable): A function that processes the given file path.
        path (str): The file path whose read-only attribute should be removed.
        _ (Any): A placeholder parameter, typically used when this function is passed 
                 as an `onexc` callback in `shutil.rmtree`.
    """
    os.chmod(path, stat.S_IWUSR)
    func(path)

def _check_input_str_list(data):
    """
    Ensures the input is a string or a list of strings. Converts a string to a single-item list,
    and validates that all elements in a list are strings.

    Args:
        data (str or list): The input data to validate and normalize.

    Returns:
        list: A list of strings.

    Raises:
        SystemExit: If input is not a string or a list of strings, triggers utils.message_exit.
    """
    if isinstance(data,str):
        return [data]
    
    elif isinstance(data,list):

        if all(isinstance(item, str) for item in data):
            return data
        utils.message_exit("Invalid input format - the variable must be a str or list of strings")
    else:

        utils.message_exit("Invalid input format - the variable must be a str or list of strings")

