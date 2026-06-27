""" README
Batch filesystem workflows built on top of low-level ops helpers.

Sections:
- shared workflow prompts and task labels
- public batch directory workflows
- internal copy, move, and unpack helpers
"""

from __future__ import annotations

__all__ = [
    "run_copy",
    "run_delete",
    "run_move",
    "run_rename",
    "run_unpack",
    "run_unpack_all_in_folder",
]

#%% === Libraries ===
import os
import re
import shutil

from typing import Any

# Insternal
from ..ops import ask, lprint
from ..ops import dirops as ops_dirops

#%% === General Tools ===

# ---------- Variables ----------
def global_variables() -> dict[str, Any]:
    """
    Return shared configuration values used by directory workflows.

    Returns:
        dict[str, Any]: Shared prompt text and action labels.
    """

    return {
        "override_question": "Do you want to overwrite existing files?",
        "delete_question": (
            "Are you sure you want to permanently delete the following paths:"
        ),
        "copy_move_labels": {
            "cp": "Copying",
            "mv": "Moving",
        },
    }


VAR = global_variables()
DirectoryPlanRow = dict[str, str | None]
DirectoryPlan = dict[int, DirectoryPlanRow]
ArchivePlan = list[list[str]]


def _resolve_override(override: bool | None) -> bool:
    """
    Resolve overwrite behavior for interactive workflows.

    Args:
        override (bool | None): Explicit overwrite preference.

    Returns:
        bool: Final overwrite mode.
    """

    if override is None:
        return ask.confirmation(VAR["override_question"])
    if isinstance(override, bool):
        return override

    lprint.error("The override option must be a boolean")
    return ask.confirmation(VAR["override_question"])


def _build_copy_move_message(
    index: int,
    total: int,
    action: str,
    src: str,
    dst: str,
    onlyfiles: str | None,
    ignorefiles: str | None,
) -> str:
    """
    Build the user-facing progress message for copy and move tasks.

    Args:
        index (int): Current task index.
        total (int): Total number of tasks.
        action (str): Action label such as ``"Copying"`` or ``"Moving"``.
        src (str): Source path.
        dst (str): Destination path.
        onlyfiles (str | None): Optional include regex.
        ignorefiles (str | None): Optional exclude regex.

    Returns:
        str: Formatted task message.
    """

    filters = []
    if onlyfiles:
        filters.append(f"Only the files that match the RegEx: {onlyfiles}")
    if ignorefiles:
        filters.append(f"Ignoring the files that match the RegEx: {ignorefiles}")

    action_line = action
    if filters:
        action_line = f"{action} - " + " - ".join(filters)

    message = [
        f"\n{'-' * 5}\nTask {index}/{total}",
        action_line,
        f"\t{src}",
        "to",
        f"\t{dst}\n",
    ]
    return "\n\t".join(message)


#%% === Workflow Helpers ===
def run_delete(
    paths: str | list[str],
    skip_confirmation: bool = False,
    force: bool = False,
) -> None:
    """
    Delete multiple paths with optional confirmation.

    Args:
        paths (str | list[str]): Target path or paths to delete.
        skip_confirmation (bool): Skip the interactive confirmation prompt.
        force (bool): Remove readonly protection before deletion when needed.
    """

    targets = _ensure_str_list(paths)
    listing = "\n".join(f"- {path}" for path in targets)
    question = f"{VAR['delete_question']}\n{listing}\n"

    confirmed = (
        skip_confirmation
        if skip_confirmation
        else ask.confirmation(question)
    )
    if confirmed:
        ops_dirops.delete_paths(targets, force=force)


def run_copy(dir_dict: DirectoryPlan, override: bool | None = None) -> None:
    """
    Copy files or directory trees from a workflow plan.

    Args:
        dir_dict (DirectoryPlan): Workflow plan containing source and
            destination rows.
        override (bool | None): Overwrite behavior.
    """

    _run_copy_or_move("cp", dir_dict, override)


def run_move(dir_dict: DirectoryPlan, override: bool | None = None) -> None:
    """
    Move files or directory trees from a workflow plan.

    Args:
        dir_dict (DirectoryPlan): Workflow plan containing source and
            destination rows.
        override (bool | None): Overwrite behavior.
    """

    _run_copy_or_move("mv", dir_dict, override)


def run_rename(dir_dict: DirectoryPlan) -> None:
    """
    Rename paths using a workflow plan.

    Args:
        dir_dict (DirectoryPlan): Workflow plan containing source and
            destination rows.
    """

    for item in dir_dict.values():
        src, dst, _, _ = _get_directory_info(item)
        if os.path.exists(src):
            ops_dirops.rename_path(src, dst)
        else:
            lprint.error(f"Directory not found.\n{src}\nSkipping task")


def run_unpack(
    dir_list: ArchivePlan,
    override: bool | None = None,
    another_unpack: int | None = None,
) -> None:
    """
    Unpack archives from a workflow list.

    Args:
        dir_list (ArchivePlan): Archive rows with ``[source]`` or
            ``[source, destination]`` shape.
        override (bool | None): Overwrite behavior.
        another_unpack (int | None): Backward-compatible unused argument.
    """

    del another_unpack
    overwrite = _resolve_override(override)

    for row in dir_list:
        src = ops_dirops.fix_path(row[0])
        dst = ops_dirops.fix_path(row[1]) if len(row) == 2 else None

        if not os.path.exists(src):
            lprint.error(f"Directory does not exist.\n{src}\nSkipping task...")
            continue

        valid_format, _ = ops_dirops.detect_unpack_format(src)
        if not valid_format:
            lprint.error(f"Format not supported.\n{src}\nSkipping task...")
            continue

        try:
            unpacked = ops_dirops.unpack_archive(src, dst, override=overwrite)
        except shutil.ReadError:
            lprint.error(f"Unable to unpack\n     {src}\nSkipping task")
            continue

        if not unpacked:
            print(f"Skipping existing destination for archive: {src}")


def run_unpack_all_in_folder(
    dir_list: list[str],
    recursive: bool = False,
    override: bool | None = False,
) -> None:
    """
    Scan folders and unpack supported archives found inside them.

    Args:
        dir_list (list[str]): Folder paths to scan for archives.
        recursive (bool): Keep rescanning until no new archives remain.
        override (bool | None): Overwrite behavior.
    """

    folders = _ensure_str_list(dir_list)
    overwrite = _resolve_override(override)

    for index, src in enumerate(folders, start=1):
        normalized_src = ops_dirops.fix_path(src)
        print(
            "\n   ".join(
                [f"{'-' * 15} Task {index}/{len(folders)}", normalized_src, ""]
            )
        )

        count = 0
        processed_files = set()

        def scan_once() -> bool:
            """
            Scan one folder pass and unpack any newly discovered archives.

            Returns:
                bool: Whether at least one archive was unpacked.
            """

            nonlocal count
            changed = False

            for dirpath, _, filenames in os.walk(normalized_src):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if file_path in processed_files:
                        continue

                    valid, _ = ops_dirops.detect_unpack_format(file_path)
                    if not valid:
                        continue

                    count += 1
                    print(f"Unpacking {count:02}:\t{file_path}")
                    run_unpack([[file_path]], override=overwrite)
                    print("|-> DONE\n")

                    processed_files.add(file_path)
                    changed = True

            return changed

        if recursive:
            while scan_once():
                pass
        else:
            scan_once()


#%% === Internal Tools ===
def _run_copy_or_move(
    option: str,
    dir_dict: DirectoryPlan,
    override: bool | None = None,
) -> None:
    """
    Execute a copy or move workflow plan.

    Args:
        option (str): Copy or move selector, either ``"cp"`` or ``"mv"``.
        dir_dict (DirectoryPlan): Workflow plan to execute.
        override (bool | None): Overwrite behavior.
    """

    overwrite = _resolve_override(override)
    action = VAR["copy_move_labels"].get(option)
    if action is None:
        raise ValueError(f"Unsupported workflow option: {option}")

    for index, item in enumerate(dir_dict.values(), start=1):
        src, dst, onlyfiles, ignorefiles = _get_directory_info(item)
        print(
            _build_copy_move_message(
                index=index,
                total=len(dir_dict),
                action=action,
                src=src,
                dst=dst,
                onlyfiles=onlyfiles,
                ignorefiles=ignorefiles,
            )
        )

        if not os.path.exists(src):
            lprint.error(f"Directory not found.\n{src}\nSkipping task")
            continue
        if ops_dirops.would_create_infloop(src, dst):
            lprint.error(f"Possible infinite loop in\n{src}\n{dst}\nSkipping task")
            continue

        if os.path.isdir(src):
            _copy_or_move_directory_tree(
                option=option,
                src=src,
                dst=dst,
                onlyfiles=onlyfiles,
                ignorefiles=ignorefiles,
                override=overwrite,
            )
            continue

        if os.path.isfile(src) and (not os.path.isfile(dst) or overwrite):
            _dispatch_copy_or_move(option, src, dst)


def _copy_or_move_directory_tree(
    option: str,
    src: str,
    dst: str,
    onlyfiles: str | None,
    ignorefiles: str | None,
    override: bool,
) -> None:
    """
    Copy or move all matching files from one directory tree to another.

    Args:
        option (str): Copy or move selector.
        src (str): Source directory.
        dst (str): Destination directory.
        onlyfiles (str | None): Optional include regex.
        ignorefiles (str | None): Optional exclude regex.
        override (bool): Overwrite behavior.
    """

    for root, _, files in os.walk(src):
        if not onlyfiles and not ignorefiles:
            rel_root = os.path.relpath(root, src)
            dst_root = os.path.join(dst, rel_root)
            os.makedirs(dst_root, exist_ok=True)

        for file_name in files:
            rel_path = os.path.relpath(os.path.join(root, file_name), src)
            if onlyfiles and not re.search(onlyfiles, file_name):
                continue
            if ignorefiles and re.search(ignorefiles, file_name):
                continue

            src_path = os.path.join(root, file_name)
            dst_path = os.path.join(dst, rel_path)

            if not override and os.path.exists(dst_path):
                continue
            _dispatch_copy_or_move(option, src_path, dst_path)

    if option == "mv":
        _remove_empty_directories(src)


def _dispatch_copy_or_move(option: str, src: str, dst: str) -> None:
    """
    Dispatch one copy or move operation to the ops layer.

    Args:
        option (str): Copy or move selector.
        src (str): Source path.
        dst (str): Destination path.
    """

    if option == "cp":
        ops_dirops.copy_path(src, dst)
        return
    if option == "mv":
        ops_dirops.move_path(src, dst)
        return
    raise ValueError(f"Unsupported workflow option: {option}")


def _remove_empty_directories(path: str) -> None:
    """
    Remove empty directories left behind after a filtered move workflow.

    Args:
        path (str): Root directory to clean up.
    """

    if not os.path.isdir(path):
        return

    for root, dirs, _ in os.walk(path, topdown=False):
        for directory in dirs:
            directory_path = os.path.join(root, directory)
            if os.path.isdir(directory_path) and not os.listdir(directory_path):
                os.rmdir(directory_path)

    if os.path.isdir(path) and not os.listdir(path):
        os.rmdir(path)


def _get_directory_info(
    item: DirectoryPlanRow,
) -> tuple[str, str, str | None, str | None]:
    """
    Extract workflow source and destination fields from one plan item.

    Args:
        item (DirectoryPlanRow): One workflow row.

    Returns:
        tuple[str, str, str | None, str | None]: Normalized source,
        destination, include regex, and exclude regex.
    """

    src = item.get("source")
    dst = item.get("destination")
    onlyfiles = item.get("onlyfiles")
    ignorefiles = item.get("ignorefiles")

    if src is None or dst is None:
        lprint.exit(
            "Each line of the file must contain 'source' and 'destination' values."
        )

    return ops_dirops.fix_path(src), ops_dirops.fix_path(dst), onlyfiles, ignorefiles


def _ensure_str_list(data: str | list[str]) -> list[str]:
    """
    Normalize a string or list of strings into a list of strings.

    Args:
        data (str | list[str]): Input value to normalize.

    Returns:
        list[str]: Normalized string list.
    """

    if isinstance(data, str):
        return [data]
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        return data
    raise TypeError("The value must be a str or list[str]")
