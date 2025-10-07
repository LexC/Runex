""" README
This file contains the core directory opetarions functions
"""
#%% === Libraries ===
import os
import re
import stat
import shutil
import pathlib
import unicodedata

from . import utils

_IMPORTED_NAMES = set(globals().keys())
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

def run_delete(paths: str | list[str], skip_confimation: bool = False, force: bool = False) -> None:
    """
    Permanently delete files and folders (including non-empty directories).

    Args:
        paths (str | list[str]): Target path or list of paths to delete.
        skip_confimation (bool): If True, delete without asking.
    """
    # --- INPUT NORMALIZATION ---
    if isinstance(paths, str):
        targets = [paths]
    elif isinstance(paths, list) and all(isinstance(p, str) for p in paths):
        targets = paths
    else:
        raise TypeError("`paths` must be a str or list[str].")

    # --- CONFIRMATION ---
    listing = "\n".join(f"- {p}" for p in targets)
    question = (
        "Are you sure you want to Permanently Delete the selected the following directories:\n"
        f"{listing}\n"
    )
    confirmation = skip_confimation if skip_confimation else utils.request_confirmation(question)

    if not confirmation:
        return

    # --- DELETE ---
    for path in targets:
        p = fix_path(path)
        if not (os.path.exists(p) or os.path.islink(p)):
            continue  # skip non-existent (incl. dangling symlink handled below)

        if os.path.islink(p) or os.path.isfile(p):
            if force:
                try:
                    os.chmod(p, stat.S_IWUSR)
                except Exception:
                    pass
            os.remove(p)
        elif os.path.isdir(p):
            if force:
                shutil.rmtree(p, onerror=_remove_readonly)
            else:
                shutil.rmtree(p)

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
        override = utils.request_confirmation("Do you want to overwrite existing files?")

    for row in dir_list:
        
        src = row[0]
        valid_format, extention = _check_valid_unpack(src)

        if len(row) == 2: dst = row[1]
        elif len(row) == 1: dst = src.removesuffix(extention)
        
        if valid_format:
            if override or not os.path.isdir(dst):
                _unpack_func(src,dst)

def run_unpack_all_in_folder(dir_list, recursive=False,override=False):
    """
    Unpack all supported archive files found under each directory in `dir_list`.

    When `recursive` is True, the directory tree is rescanned until no new
    archives remain (handles nested archives). If `override` is None, the user
    is prompted to decide whether to overwrite existing files.

    Args:
        dir_list (list[str]): Directories to scan for candidate archives.
        recursive (bool, optional): If True, keep rescanning for newly created
            archives. Defaults to False.
        override (bool | None, optional): Overwrite behavior; if None, prompt
            the user. Defaults to False.

    Returns:
        None
    """
    # --- SETUP AND VALIDATION ---
    # Normalize override behavior: allow interactive prompt when set to None
    if override is None:
        override = utils.request_confirmation(
            "Do you want to overwrite existing files?"
        )
    
    # --- LOGIC ---
    for idx, src in enumerate(dir_list, start=1):
        print("\n   ".join([f"{'-'*50}/nTask {idx}/{len(dir_list)}", src, ""]))

        count = 0
        processed_files = set()  

        def scan_once() -> bool:
            """Scan `src` once; unpack any valid, not-yet-processed archives.
            Returns True if at least one file was unpacked in this pass."""
            nonlocal count
            changed = False

            for dirpath, _, filenames in os.walk(src):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)

                    # Skip if already processed this run
                    if file_path in processed_files:
                        continue

                    valid, _ = _check_valid_unpack(file_path, silent=True)
                    if not valid:
                        continue

                    count += 1
                    print(f"Unpacking {count:02}:\t{file_path}")
                    # `run_unpack` expects a nested list [[path]]
                    run_unpack([[file_path]], override=override, another_unpack=1)
                    print("|-> DONE\n")

                    processed_files.add(file_path)
                    changed = True

            return changed

        if recursive:
            # Keep scanning while each pass finds new archives (nested extraction)
            while scan_once():
                # Loop until a full pass yields no new work
                pass
        else:
            # Single pass only
            scan_once()

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
        override = utils.request_confirmation("Do you want to overwrite existing files?")
    elif type(override) != bool:
        utils.message_error('The override option must be a boolian')
        override = utils.request_confirmation("Do you want to overwrite existing files?")


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

#%% === Checks and Validations ===

# ---------- Public ----------

def validate_file_path(file_path: str, supported_extensions: list[str] = None) -> str:
    """
    Repeatedly prompts until a valid file path is provided. Optionally validates file extension.

    Args:
        file_path (str): Initial path to validate.
        supported_extensions (list[str], optional): List of valid extensions or a string extension.

    Returns:
        str: A validated file path.
    """
    file_path = fix_path(file_path)

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

        file_path = fix_path(utils.request_input("Please enter a valid file path: "))

    return file_path

#%% === Support ===

# ---------- Public ----------

def fix_path(path: str, ascii_only: bool = False, remove_globs: bool = True) -> str:
    """
    Sanitize a path string (optionally ASCII-only) and then convert it to the
    current OS style via `_convert_path_to_current_os`.

    Sanitization rules:
        - Remove Unicode zero-width chars (U+200B-U+200D, U+FEFF).
        - Remove control chars (U+0000-U+001F, U+007F).
        - Strip leading/trailing whitespace.
        - If `ascii_only` is True: remove non-ASCII characters;
          otherwise normalize Unicode to NFC (keeps accents).
        - Remove illegal filename chars:
            * Always remove: < > " |
            * Additionally remove `?` and `*` if `remove_globs` is True
              (these are invalid on Windows and can trigger globbing).

    Args:
        path (str): Raw input path.
        ascii_only (bool): If True, drop non-ASCII; else keep Unicode (NFC).
        remove_globs (bool): If True, also remove `?` and `*`. Defaults to True.

    Returns:
        str: A sanitized, OS-appropriate path string.

    Notes:
        - Delegates platform-specific shaping to `_convert_path_to_current_os`.
        - Colons (:) are not removed to avoid breaking `C:` and POSIX names.
    """
    # --- SETUP AND VALIDATION ---
    if not isinstance(path, str) or not path:
        utils.message_warning(f'Path {path!r} is not a valid string.')
        return path

    # --- PATH SANITIZATION ---
    path = path.strip()                                   # Trim edges
    path = re.sub(r"[\u200B-\u200D\uFEFF]", "", path)     # Zero-width chars
    path = re.sub(r"[\x00-\x1F\x7F]", "", path)           # Control chars

    if ascii_only:
        path = re.sub(r"[^\x00-\x7F]", "", path)          # Enforce ASCII
    else:
        path = unicodedata.normalize("NFC", path)         # Keep accents

    # Remove illegal filename chars (keep separators and colons)
    illegal_class = r'[<>"|?*]' if remove_globs else r'[<>"|]'
    path = re.sub(illegal_class, "", path)

    # --- CONVERT TO CURRENT OS ---
    return _convert_path_to_current_os(path)


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

def _convert_path_to_current_os(path: str) -> str:
    """
    Detects the input path style (Windows, UNC, device/extended, WSL, POSIX, or
    relative) and converts it to a form appropriate for the *current* host OS.

    Supported detections:
        - windows_extended:    Paths like \\\\?\\C:\\path\\to\\file
        - windows_device:      Paths like \\\\.\\COM1
        - windows_unc:         Paths like \\\\server\\share\\...
        - windows_drive_abs:   Paths like C:\\folder\\file or C:/folder/file
        - windows_drive_rel:   Paths like C:folder\\file (no slash after colon)
        - wsl:                 Paths like /mnt/c/path/...
        - posix_abs:           Absolute POSIX paths like /usr/bin/...
        - relative:            Paths without a leading drive/anchor

    Args:
        path (str): Raw input path string.

    Returns:
        str: Path converted to an OS-appropriate form. If the input is falsy,
            returns it unchanged.

    Notes:
        * On Windows hosts:
            - Preserves extended/device paths as-is.
            - Converts WSL (/mnt/<drive>/...) to drive-letter form (e.g., C:\\...).
            - Normalizes separators to backslashes and collapses redundant
            separators; fixes C:folder -> C:\\folder.
            - Keeps UNC paths with canonical leading backslashes.
        * On POSIX hosts:
            - Converts UNC (\\\\server\\share\\...) to //server/share/... form.
            - Converts C:\\... (or C:/...) to /mnt/<drive>/... when running on
            Linux; C:folder is treated as C:\\folder first.
            - Otherwise normalizes to forward slashes.
    """
    # --- SETUP AND VALIDATION ---
    if not path:
        return path

    # Define OS booleans
    is_windows = (os.name == "nt")
    is_posix = (os.name == "posix")
    is_linux = is_posix and os.uname().sysname == "Linux"

    # Define regex patterns for detection
    patterns = {
        "windows_extended": re.compile(r"^\\\\\?\\\\"),
        "windows_device": re.compile(r"^\\\\\.\\\\"),
        "windows_unc": re.compile(r"^\\\\\\\\"),
        "windows_drive_abs": re.compile(r"^[A-Za-z]:[\\/]"),
        "windows_drive_rel": re.compile(r"^[A-Za-z]:(?![\\/])"),
        "wsl": re.compile(r"^/mnt/[a-z]/"),
    }
    
    # DETECT PATH TYPE
    ptype = "relative"
    for name, pattern in patterns.items():
        if pattern.match(path):
            ptype = name
            break
    
    # --- WINDOWS HOST ---
    if is_windows:
        if ptype == "windows_unc":
            # Keep UNC with backslashes and canonical leading \\ prefix
            body = re.sub(r"[\\/]+", r"\\", path[2:])
            unc  = "\\\\" + body
            return os.path.normpath(unc) 
        if ptype == "wsl":
            # /mnt/c/foo/bar -> C:\foo\bar
            m = re.match(r"^/mnt/([a-z])/(.*)", path)
            if m:
                drive = m.group(1).upper()
                rest = m.group(2).replace("/", "\\")
                return os.path.normpath(f"{drive}:\\{rest}")
        if ptype == "windows_drive_rel":
            # C:folder\file -> C:\folder\file
            fixed = path[:2] + "\\" + path[2:]
            return os.path.normpath(fixed.replace("/", "\\"))
        if ptype in ("windows_extended", "windows_device"):
            # Pass through as-is; caller expects raw extended/device paths.
            return path
        # Default: normalize to backslashes
        return os.path.normpath(path.replace("/", "\\"))
    
    # --- POSIX HOST ---
    elif is_posix:
        if ptype == "windows_unc":
            # \\server\share\dir\file -> //server/share/dir/file (Samba-style)
            body = path[2:].replace("\\", "/")
            smb  = "//" + re.sub(r"/{2,}", "/", body)
            return os.path.normpath(smb)
        if ptype == "windows_drive_rel":
            # C:folder\file -> treat as C:\folder\file then convert to /mnt/c/...
            path = path[:2] + "\\" + path[2:]
            ptype = "windows_drive_abs"  # fall-through to next block
        if ptype == "windows_drive_abs" and is_linux:
            # C:\foo\bar or C:/foo/bar -> /mnt/c/foo/bar
            drive = path[0].lower()
            rest = path[2:].replace("\\", "/").lstrip("/")
            return os.path.normpath(f"/mnt/{drive}/{rest}")
        # Default: normalize to forward slashes
        return os.path.normpath(path.replace("\\", "/"))

    # --- FALLBACK ---
    return path

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
