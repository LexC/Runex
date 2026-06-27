""" README
Interactive prompt helpers for terminal workflows.

Sections:
- shared prompt configuration
- public input helpers
- internal option helpers
"""

from __future__ import annotations

__all__ = [
    "confirmation",
    "input",
    "option",
]

#%% === Libraries ===
import builtins
from typing import Any

# Insternal
from . import common, lprint

#%% === General Tools ===

# ---------- Variables ----------
VAR = {
    "invalid_confirmation_message": "Please enter 'yes' or 'no'.",
    "options_header": "Please choose from the following options:",
    "option_prompt": "Select by number or name/key: ",
}


#%% === Prompt Helpers ===
def input(prompt_message: str) -> str:
    """
    Request raw input from the user.

    Args:
        prompt_message (str): Prompt shown in the terminal.

    Returns:
        str: Raw user input.
    """

    lprint.lprint(prompt_message, end="", flush=True, log=False)
    return builtins.input()


def confirmation(question: str) -> bool:
    """
    Request a yes or no confirmation from the user.

    Args:
        question (str): Confirmation question.

    Returns:
        bool: Parsed confirmation result.
    """

    while True:
        response = common.str2bool(input(f"{question} (yes/no): ").strip().lower(), silent=True)
        if response is not None:
            return response
        lprint.lprint(VAR["invalid_confirmation_message"])


def option(
    options: dict | list,
    descriptions: list | None = None,
    loop: bool = True,
) -> Any | None:
    """
    Display options and request one selection by index or key.

    Args:
        options (dict | list): Available options.
        descriptions (list | None): Optional descriptions for list input.
        loop (bool): Whether to keep prompting on invalid input.

    Returns:
        Any | None: Selected option key or value.
    """

    keys, items = _normalize_option_items(options, descriptions)

    lprint.lprint(VAR["options_header"])
    for index, (key, description) in enumerate(items, start=1):
        display = f"\t{index}. {key}"
        if description:
            display += f": {description}"
        lprint.lprint(display)

    while True:
        user_input = input(VAR["option_prompt"]).strip()
        if user_input.isdigit():
            option_index = int(user_input) - 1
            if 0 <= option_index < len(keys):
                return keys[option_index]

        if user_input in keys:
            return user_input

        if not loop:
            lprint.lprint("Invalid selection.")
            return None
        lprint.lprint("Invalid selection. Please try again.")


#%% === Internal Tools ===
def _normalize_option_items(
    options: dict | list,
    descriptions: list | None = None,
) -> tuple[list, list[tuple[Any, Any]]]:
    """
    Normalize list or dictionary options into a display-ready structure.

    Args:
        options (dict | list): Options accepted by ``option``.
        descriptions (list | None): Optional descriptions used with list input.

    Returns:
        tuple[list, list[tuple[Any, Any]]]: Ordered keys and display items.
    """

    if isinstance(options, dict):
        if not options:
            lprint.exit("The input dictionary cannot be empty.")
        return list(options.keys()), list(options.items())

    if isinstance(options, list):
        if not options:
            lprint.exit("The input list cannot be empty.")

        if descriptions is None:
            return options, [(option, "") for option in options]

        items = []
        for index, option in enumerate(options):
            description = descriptions[index] if index < len(descriptions) else ""
            items.append((option, description))
        return options, items

    lprint.exit("Options must be a list or a dictionary.")
    raise AssertionError("unreachable")
