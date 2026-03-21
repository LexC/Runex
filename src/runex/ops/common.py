""" README
Shared non-I/O helpers for the ops layer.

Sections:
- shared text parsing settings
- normalization and conversion helpers
- matching and validation helpers
"""

from __future__ import annotations

__all__ = [
    "lowercase_keys_in_dict",
    "match_terms_to_text",
    "str2bool",
    "str2float",
    "str_normalize",
    "strip_whitespaces",
    "validate_string",
]

#%% === Libraries ===
import re
import unicodedata

#%% === General Tools ===

# ---------- Variables ----------
def global_variables() -> dict[str, set[str] | list[str]]:
    """
    Return shared constants used across text helper functions.

    Returns:
        dict[str, set[str] | list[str]]: Truthy and falsy string groups plus
        default ignored search terms.
    """

    return {
        "truthy_values": {"true", "yes", "1", "y"},
        "falsy_values": {"false", "no", "0", "n"},
        "default_ignore_terms": [" ", ""],
    }


VAR = global_variables()


#%% === Text Helpers ===
def str_normalize(
    text: str,
    lower: bool = False,
    valid_chars: str = "_.|()[]{}-",
) -> str:
    """
    Normalize a string for matching and comparison.

    Args:
        text (str): Input string to normalize.
        lower (bool): Convert the output to lowercase when ``True``.
        valid_chars (str): Extra non-alphanumeric characters to preserve.

    Returns:
        str: Normalized string value.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    normalized_text = text.strip()
    normalized_text = unicodedata.normalize("NFKD", normalized_text)
    normalized_text = normalized_text.encode("ASCII", "ignore").decode("utf-8")

    if lower:
        normalized_text = normalized_text.lower()

    normalized_text = re.sub(
        rf"[^a-zA-Z0-9\s{re.escape(valid_chars)}]",
        " ",
        normalized_text,
    )
    return re.sub(r"\s+", " ", normalized_text)


def strip_whitespaces(text: str) -> str:
    """
    Remove all whitespace from a string.

    Args:
        text (str): Input string.

    Returns:
        str: String with all whitespace removed.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return re.sub(r"\s+", "", text)


def str2float(number_str: object) -> float | None:
    """
    Convert a string or numeric value to float.

    Args:
        number_str (object): Value to convert.

    Returns:
        float | None: Parsed float value, or ``None`` for unsupported inputs.
    """

    if isinstance(number_str, str):
        cleaned_value = number_str.strip().replace(",", "")
        return float(cleaned_value)
    if isinstance(number_str, (int, float)):
        return float(number_str)
    return None


def str2bool(value: object) -> bool | None:
    """
    Convert common truthy and falsy string inputs to ``bool``.

    Args:
        value (object): Value to evaluate.

    Returns:
        bool | None: Converted boolean value, or ``None`` when unknown.
    """

    if isinstance(value, bool):
        return value

    normalized_value = str(value).strip().lower()
    if normalized_value in VAR["truthy_values"]:
        return True
    if normalized_value in VAR["falsy_values"]:
        return False
    return None


#%% === Matching Helpers ===
def match_terms_to_text(
    text: str,
    search_terms: list[str],
    normalize: bool = True,
    valid_chars: str | None = None,
    silent: bool = True,
    ignore_terms: list[str] | str = "default",
) -> bool:
    """
    Return ``True`` when any candidate term matches the input text.

    Args:
        text (str): Input text to search.
        search_terms (list[str]): Candidate search terms.
        normalize (bool): Normalize text and terms before matching.
        valid_chars (str | None): Characters to preserve during normalization.
        silent (bool): Preserved for backward compatibility.
        ignore_terms (list[str] | str): Terms to ignore during matching.

    Returns:
        bool: Whether any search term matches the input text.
    """

    del silent

    if not isinstance(text, str) or not isinstance(search_terms, list):
        return False

    normalized_ignore_terms = _resolve_ignore_terms(ignore_terms)
    if normalize:
        if valid_chars is None:
            normalized_text = str_normalize(text, lower=True)
            normalized_terms = [
                str_normalize(term, lower=True) for term in search_terms
            ]
        else:
            normalized_text = str_normalize(text, lower=True, valid_chars=valid_chars)
            normalized_terms = [
                str_normalize(term, lower=True, valid_chars=valid_chars)
                for term in search_terms
            ]
    else:
        normalized_text = text
        normalized_terms = search_terms

    for term in normalized_terms:
        if term in normalized_ignore_terms:
            continue

        escaped_pattern = re.escape(term)
        if " " in term:
            if re.search(escaped_pattern, normalized_text):
                return True
            continue

        if re.search(rf"\b{escaped_pattern}\b", normalized_text):
            return True

    return False


def validate_string(
    value: str,
    allowed_options: list[str],
    case_sensitive: bool = False,
) -> str:
    """
    Validate a string against a list of allowed values.

    Args:
        value (str): Candidate value.
        allowed_options (list[str]): Accepted options.
        case_sensitive (bool): Match with case sensitivity when ``True``.

    Returns:
        str: Original validated value.
    """

    if not isinstance(allowed_options, list) or not all(
        isinstance(option, str) for option in allowed_options
    ):
        raise TypeError("allowed_options must be a list of strings")
    if not isinstance(value, str):
        raise TypeError("value must be a string")

    value_to_check = value if case_sensitive else value.lower()
    options_to_check = (
        allowed_options
        if case_sensitive
        else [option.lower() for option in allowed_options]
    )

    if value_to_check not in options_to_check:
        raise ValueError(
            f"Invalid option: {value}. Allowed options are: "
            f"{', '.join(allowed_options)}"
        )

    return value


def lowercase_keys_in_dict(
    target_dict: dict,
    keys_to_lowercase: list[str],
) -> None:
    """
    Lowercase selected nested-dict keys in place.

    Args:
        target_dict (dict): Dictionary containing inner dictionaries.
        keys_to_lowercase (list[str]): Keys that should be forced to lowercase.
    """

    normalized_keys = {key.lower() for key in keys_to_lowercase}
    for inner_dict in target_dict.values():
        keys_to_fix = [
            key for key in inner_dict.keys() if key.lower() in normalized_keys
        ]
        for key in keys_to_fix:
            lower_key = key.lower()
            if lower_key != key:
                inner_dict[lower_key] = inner_dict.pop(key)


#%% === Internal Tools ===
def _resolve_ignore_terms(ignore_terms: list[str] | str) -> list[str]:
    """
    Normalize ignored term configuration for text matching.

    Args:
        ignore_terms (list[str] | str): Ignore term definition.

    Returns:
        list[str]: Normalized ignore terms list.
    """

    if ignore_terms == "default":
        return VAR["default_ignore_terms"]
    if isinstance(ignore_terms, str):
        return [ignore_terms]
    if isinstance(ignore_terms, list):
        return ignore_terms
    raise TypeError("ignore_terms must be 'default', a string, or a list")
