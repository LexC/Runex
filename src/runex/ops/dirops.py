""" README
Low-level filesystem and path helpers for the ops layer.

Sections:
- shared path normalization settings
- filesystem operations
- path inspection and search helpers
- internal normalization helpers
"""

from __future__ import annotations

__all__ = [
    "copy_path",
    "delete_paths",
    "detect_unpack_format",
    "find_files_by_regex",
    "fix_path",
    "get_parent_folder_by_level",
    "locate_files_by_extension",
    "locate_files_by_name_pattern",
    "make_dir_dict",
    "move_path",
    "rename_path",
    "run_mkdir",
    "unpack_archive",
    "validate_file_path",
    "would_create_infloop",
]

#%% === Libraries ===
import os
import re
import stat
import shutil
import unicodedata

from typing import Any
from pathlib import Path

#%% === General Tools ===

# ---------- Variables ----------
def global_variables() -> dict[str, Any]:
    """
    Return shared configuration values used across path helpers.

    Returns:
        dict[str, Any]: Precompiled regex patterns and shared path settings.
    """

    return {
        "unicode_strip_pattern": re.compile(r"[\u200B-\u200D\uFEFF]"),
        "control_char_pattern": re.compile(r"[\x00-\x1F\x7F]"),
        "illegal_path_patterns": {
            True: re.compile(r'[<>"|?*]'),
            False: re.compile(r'[<>"|]'),
        },
        "path_patterns": {
            "windows_extended": re.compile(r"^\\\\\?\\\\"),
            "windows_device": re.compile(r"^\\\\\.\\\\"),
            "windows_unc": re.compile(r"^\\\\\\\\"),
            "windows_drive_abs": re.compile(r"^[A-Za-z]:[\\/]"),
            "windows_drive_rel": re.compile(r"^[A-Za-z]:(?![\\/])"),
            "wsl": re.compile(r"^/mnt/[a-z]/"),
        },
    }


VAR = global_variables()


#%% === Filesystem Operations ===
def run_mkdir(dir_list: str | list[str]) -> None:
    """
    Create one or more directories, including parent directories.

    Args:
        dir_list (str | list[str]): Directory path or list of directory paths.
    """

    for directory in _ensure_str_list(dir_list):
        os.makedirs(fix_path(directory), exist_ok=True)


def delete_paths(paths: str | list[str], force: bool = False) -> None:
    """
    Delete files, symlinks, or directories without prompting.

    Args:
        paths (str | list[str]): One path or a list of paths to delete.
        force (bool): Remove readonly protection before deletion when needed.
    """

    for path in _ensure_str_list(paths):
        normalized_path = fix_path(path)
        if not (os.path.exists(normalized_path) or os.path.islink(normalized_path)):
            continue

        if os.path.islink(normalized_path) or os.path.isfile(normalized_path):
            if force:
                try:
                    os.chmod(normalized_path, stat.S_IWUSR)
                except OSError:
                    pass
            os.remove(normalized_path)
            continue

        if os.path.isdir(normalized_path):
            if force:
                shutil.rmtree(normalized_path, onerror=_remove_readonly)
            else:
                shutil.rmtree(normalized_path)


def copy_path(src: str, dst: str) -> None:
    """
    Copy a file or directory tree from source to destination.

    Args:
        src (str): Source file or directory path.
        dst (str): Destination file or directory path.
    """

    src = fix_path(src)
    dst = fix_path(dst)

    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return

    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copy2(src, dst)


def move_path(src: str, dst: str) -> None:
    """
    Move a file or directory tree from source to destination.

    Args:
        src (str): Source file or directory path.
        dst (str): Destination file or directory path.
    """

    src = fix_path(src)
    dst = fix_path(dst)
    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.move(src, dst)


def rename_path(src: str, dst: str) -> None:
    """
    Rename one filesystem path.

    Args:
        src (str): Existing path.
        dst (str): New path.
    """

    os.rename(fix_path(src), fix_path(dst))


def unpack_archive(
    src: str,
    dst: str | None = None,
    *,
    override: bool = True,
) -> bool:
    """
    Unpack one archive into the target directory.

    Args:
        src (str): Archive file path.
        dst (str | None): Optional destination directory.
        override (bool): Whether an existing destination may be replaced.

    Returns:
        bool: ``True`` when unpacking was performed, otherwise ``False``.

    Raises:
        ValueError: If the archive format is not supported.
    """

    src = fix_path(src)
    valid_format, extension = detect_unpack_format(src)
    if not valid_format:
        raise ValueError(f"Unsupported archive format: {src}")

    destination = src.removesuffix(extension) if dst is None else fix_path(dst)
    if not override and os.path.isdir(destination):
        return False

    shutil.unpack_archive(src, destination)
    return True


#%% === Path Helpers ===
def locate_files_by_extension(folder_path: str, extension: str) -> list[Path]:
    """
    Find files in a directory by file extension.

    Args:
        folder_path (str): Folder to search.
        extension (str): Extension to match, with or without the leading dot.

    Returns:
        list[Path]: Matching paths inside the target folder.
    """

    folder = Path(fix_path(folder_path))
    normalized_extension = extension.lstrip(".")
    return list(folder.glob(f"*.{normalized_extension}"))


def locate_files_by_name_pattern(folder_path: str, filename: str) -> list[Path]:
    """
    Find files in a directory by partial filename.

    Args:
        folder_path (str): Folder to search.
        filename (str): Partial file name to match.

    Returns:
        list[Path]: Matching paths inside the target folder.
    """

    folder = Path(fix_path(folder_path))
    return list(folder.glob(f"*{filename}*"))


def validate_file_path(
    file_path: str,
    supported_extensions: list[str] | str | None = None,
) -> str:
    """
    Validate that a path exists, is a file, and matches any required extension.

    Args:
        file_path (str): File path to validate.
        supported_extensions (list[str] | str | None): Optional allowed
            extensions.

    Returns:
        str: Normalized file path.
    """

    if not isinstance(file_path, str):
        raise TypeError("file_path must be a string")

    normalized_path = fix_path(file_path)
    if not os.path.exists(normalized_path):
        raise FileNotFoundError(normalized_path)
    if not os.path.isfile(normalized_path):
        raise IsADirectoryError(normalized_path)

    if supported_extensions is not None:
        if isinstance(supported_extensions, str):
            supported_extensions = [supported_extensions]

        normalized_extensions = [extension.lower() for extension in supported_extensions]
        _, extension = os.path.splitext(normalized_path)
        if extension.lower() not in normalized_extensions:
            raise ValueError(f"Unsupported file extension: {extension}")

    return normalized_path


def fix_path(path: str, ascii_only: bool = False, remove_globs: bool = True) -> str:
    """
    Sanitize a path string and convert it to the current OS path style.

    Args:
        path (str): Raw filesystem path.
        ascii_only (bool): Remove non-ASCII characters when ``True``.
        remove_globs (bool): Remove wildcard characters when ``True``.

    Returns:
        str: Cleaned filesystem path.
    """

    if not isinstance(path, str) or not path:
        raise TypeError("path must be a non-empty string")

    cleaned_path = path.strip()
    cleaned_path = VAR["unicode_strip_pattern"].sub("", cleaned_path)
    cleaned_path = VAR["control_char_pattern"].sub("", cleaned_path)

    if ascii_only:
        cleaned_path = re.sub(r"[^\x00-\x7F]", "", cleaned_path)
    else:
        cleaned_path = unicodedata.normalize("NFC", cleaned_path)

    illegal_pattern = VAR["illegal_path_patterns"][remove_globs]
    cleaned_path = illegal_pattern.sub("", cleaned_path)
    return _convert_path_to_current_os(cleaned_path)


def get_parent_folder_by_level(path: str, level: int) -> str:
    """
    Get the parent folder name at a given depth.

    Args:
        path (str): Base filesystem path.
        level (int): Depth relative to the end of the path.

    Returns:
        str: Parent folder name at the requested depth.
    """

    if not isinstance(level, int):
        raise TypeError("level must be an integer")
    if level < 0:
        raise ValueError("level must be zero or greater")

    normalized_path = fix_path(path)
    parts = os.path.normpath(normalized_path).split(os.sep)
    if len(parts) >= level + 1:
        return parts[-(level + 1)]

    raise ValueError("Parent not found")


def find_files_by_regex(
    base_path: str,
    file_pattern: str,
    recursive: bool = True,
) -> list[str]:
    """
    Return file paths matching a regex pattern.

    Args:
        base_path (str): Directory to search.
        file_pattern (str): Regex applied to file names.
        recursive (bool): Search subdirectories when ``True``.

    Returns:
        list[str]: Matching file paths.
    """

    normalized_base_path = fix_path(base_path)
    file_regex = re.compile(file_pattern)
    matched_files: list[str] = []

    if recursive:
        for root, _, files in os.walk(normalized_base_path):
            for file_name in files:
                if file_regex.match(file_name):
                    matched_files.append(os.path.join(root, file_name))
        return matched_files

    for file_name in os.listdir(normalized_base_path):
        full_path = os.path.join(normalized_base_path, file_name)
        if os.path.isfile(full_path) and file_regex.match(file_name):
            matched_files.append(full_path)

    return matched_files


def make_dir_dict(
    source: str | list[str],
    destination: str | list[str],
    onlyfiles: str | list[str] | None = None,
    ignorefiles: str | list[str] | None = None,
) -> dict[int, dict[str, str | None]]:
    """
    Create a normalized source/destination workflow plan dictionary.

    Args:
        source (str | list[str]): Source path or source paths.
        destination (str | list[str]): Destination path or destination paths.
        onlyfiles (str | list[str] | None): Optional include regex per row.
        ignorefiles (str | list[str] | None): Optional exclude regex per row.

    Returns:
        dict[int, dict[str, str | None]]: Workflow plan dictionary.
    """

    if isinstance(source, str):
        if not isinstance(destination, str):
            raise TypeError("The types of the input variables do not match")
        if onlyfiles is not None and not isinstance(onlyfiles, str):
            raise TypeError("The types of the input variables do not match")
        if ignorefiles is not None and not isinstance(ignorefiles, str):
            raise TypeError("The types of the input variables do not match")

        return {
            0: {
                "source": source,
                "destination": destination,
                "onlyfiles": onlyfiles,
                "ignorefiles": ignorefiles,
            }
        }

    source_list = _ensure_str_list(source)
    destination_list = _ensure_str_list(destination)
    onlyfiles_list = _ensure_optional_str_list(onlyfiles, "onlyfiles")
    ignorefiles_list = _ensure_optional_str_list(ignorefiles, "ignorefiles")

    if len(source_list) != len(destination_list):
        raise ValueError("source and destination lists must have the same length")

    if onlyfiles_list is None:
        onlyfiles_list = [None] * len(source_list)
    elif len(onlyfiles_list) != len(source_list):
        raise ValueError("onlyfiles must match the length of source")

    if ignorefiles_list is None:
        ignorefiles_list = [None] * len(source_list)
    elif len(ignorefiles_list) != len(source_list):
        raise ValueError("ignorefiles must match the length of source")

    dir_dict: dict[int, dict[str, str | None]] = {}
    for index, (src, dst, onlf, ignf) in enumerate(
        zip(source_list, destination_list, onlyfiles_list, ignorefiles_list)
    ):
        dir_dict[index] = {
            "source": src,
            "destination": dst,
            "onlyfiles": onlf,
            "ignorefiles": ignf,
        }

    return dir_dict


def detect_unpack_format(path: str) -> tuple[bool, str]:
    """
    Detect whether a path has a supported archive extension.

    Args:
        path (str): Candidate archive path.

    Returns:
        tuple[bool, str]: Match flag and matched unpack extension.
    """

    normalized_path = fix_path(path)
    if not os.path.exists(normalized_path):
        return False, ""

    normalized_lower = normalized_path.lower()
    for _, extensions, _ in shutil.get_unpack_formats():
        for extension in extensions:
            if normalized_lower.endswith(extension.lower()):
                return True, extension

    return False, ""


def would_create_infloop(src: str, dst: str) -> bool:
    """
    Return ``True`` when destination is inside the source tree.

    Args:
        src (str): Source directory path.
        dst (str): Destination path.

    Returns:
        bool: Whether the destination would create a recursive copy target.
    """

    src = fix_path(src)
    dst = fix_path(dst)
    if not os.path.isdir(src):
        return False

    src_abs = os.path.abspath(src)
    dst_abs = os.path.abspath(dst)

    try:
        return os.path.commonpath([src_abs, dst_abs]) == src_abs and src_abs != dst_abs
    except ValueError:
        return False


#%% === Internal Tools ===
def _convert_path_to_current_os(path: str) -> str:
    """
    Convert a path from common Windows, WSL, or POSIX formats to the host format.

    Args:
        path (str): Path string to convert.

    Returns:
        str: Normalized host-style path.
    """

    if not path:
        return path

    is_windows = os.name == "nt"
    is_posix = os.name == "posix"
    is_linux = is_posix and os.uname().sysname == "Linux"

    path_type = "relative"
    for name, pattern in VAR["path_patterns"].items():
        if pattern.match(path):
            path_type = name
            break

    if is_windows:
        if path_type == "windows_unc":
            body = re.sub(r"[\\/]+", r"\\", path[2:])
            return os.path.normpath("\\\\" + body)
        if path_type == "wsl":
            match = re.match(r"^/mnt/([a-z])/(.*)", path)
            if match:
                drive = match.group(1).upper()
                rest = match.group(2).replace("/", "\\")
                return os.path.normpath(f"{drive}:\\{rest}")
        if path_type == "windows_drive_rel":
            fixed = path[:2] + "\\" + path[2:]
            return os.path.normpath(fixed.replace("/", "\\"))
        if path_type in {"windows_extended", "windows_device"}:
            return path
        return os.path.normpath(path.replace("/", "\\"))

    if is_posix:
        if path_type == "windows_unc":
            body = path[2:].replace("\\", "/")
            return os.path.normpath("//" + re.sub(r"/{2,}", "/", body))
        if path_type == "windows_drive_rel":
            path = path[:2] + "\\" + path[2:]
            path_type = "windows_drive_abs"
        if path_type == "windows_drive_abs" and is_linux:
            drive = path[0].lower()
            rest = path[2:].replace("\\", "/").lstrip("/")
            return os.path.normpath(f"/mnt/{drive}/{rest}")
        return os.path.normpath(path.replace("\\", "/"))

    return path


def _remove_readonly(func, path: str, _) -> None:
    """
    Clear the readonly bit and retry a filesystem operation.

    Args:
        func: Callback provided by ``shutil.rmtree``.
        path (str): Target path.
        _: Ignored exception info tuple.
    """

    os.chmod(path, stat.S_IWUSR)
    func(path)


def _ensure_str_list(data: str | list[str]) -> list[str]:
    """
    Normalize a string or list of strings into a list of strings.

    Args:
        data (str | list[str]): Input path or path list.

    Returns:
        list[str]: Normalized list form.
    """

    if isinstance(data, str):
        return [data]
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        return data
    raise TypeError("The value must be a str or list[str]")


def _ensure_optional_str_list(
    data: list[str | None] | None | str,
    field_name: str,
) -> list[str | None] | None:
    """
    Validate an optional string list used in workflow plan rows.

    Args:
        data (list[str | None] | None | str): Optional list-like field.
        field_name (str): Field name used in error messages.

    Returns:
        list[str | None] | None: Validated list value or ``None``.
    """

    if data is None:
        return None
    if isinstance(data, list) and all(item is None or isinstance(item, str) for item in data):
        return data
    raise TypeError(f"{field_name} must be None or list[str | None]")
