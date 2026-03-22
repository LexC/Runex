""" README
Shared non-I/O helpers for the ops layer.

Sections:
- shared text parsing settings
- optional import helpers
- normalization and conversion helpers
- matching and validation helpers
"""

from __future__ import annotations

__all__ = [
    "abbr2number",
    "import_lib",
    "lowercase_keys_in_dict",
    "match_terms_to_text",
    "number2abbr",
    "str2bool",
    "str2float",
    "str_normalize",
    "strip_whitespaces",
    "validate_installed_lib",
    "validate_string",
]

#%% === Libraries ===
import re
import math
import importlib
import importlib.util
import unicodedata

from typing import Any

#%% === General Tools ===

# ---------- Variables ----------
def global_variables() -> dict[str,Any]:
    """
    Return shared constants used across text helper functions.

    Returns:
        dict[str, Any]: Shared string parsing groups, ignored
            search terms, default preserved characters, and compact-number
            suffix factors.
    """

    return {
        "truthy_values": {"true", "yes", "1", "y"},
        "falsy_values": {"false", "no", "0", "n"},
        "default_ignore_terms": [" ", ""],
        "default_valid_chars": r"_.|()[]{}-",
        "number_suffix_factors": {
            "p": 1e-12,
            "n": 1e-9,
            "u": 1e-6,
            "m": 1e-3,
            "" : 1,
            "K": 1e3,
            "M": 1e6,
            "B": 1e9,
            "T": 1e12,
        },
    }
VAR = global_variables()


#%% === Optional Import Helpers ===

def validate_installed_lib(lib_name: str) -> bool:
    """
    Return whether a library is importable.

    Args:
        lib_name (str): Library name to validate.

    Returns:
        bool: Whether the requested library is importable.
    """
    normalized_lib_name = _normalize_lib_name(lib_name)
    return importlib.util.find_spec(normalized_lib_name) is not None


def import_lib(lib_name: str,silent: bool = True) -> object | None:
    """
    Import a library on demand.

    Args:
        lib_name (str): Library reference in one of these forms: `X`,
            `import X`, `import X as Y`, `from Z import X`, or
            `from Z import X as Y`.
        silent (bool): Return `None` for missing libraries when `True`.
            Defaults to `True`.

    Returns:
        object | None: Imported module object, or `None` when the library is
            missing in silent mode.

    Raises:
        ModuleNotFoundError: Raised when a requested library is not installed
            and `silent=False`.
    """

    normalized_lib_name = _normalize_lib_name(lib_name)
    candidate_names = [normalized_lib_name]
    module_path_pattern = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*"
    alias_pattern = r"[A-Za-z_]\w*"

    from_import_match = re.fullmatch(
        rf"from\s+(?P<base>{module_path_pattern})\s+import\s+"
        rf"(?P<imported>{alias_pattern})(?:\s+as\s+(?P<alias>{alias_pattern}))?",
        normalized_lib_name,
    )
    if from_import_match:
        base_name = from_import_match.group("base")
        imported_name = from_import_match.group("imported")

        candidate_names = [base_name]
        if imported_name:
            candidate_names.insert(0, f"{base_name}.{imported_name}")
    else:
        import_match = re.fullmatch(
            rf"import\s+(?P<imported>{module_path_pattern})"
            rf"(?:\s+as\s+(?P<alias>{alias_pattern}))?",
            normalized_lib_name,
        )
        if import_match:
            imported_name = import_match.group("imported")
            if imported_name:
                candidate_names = [imported_name]

    normalized_lib_name = None
    for candidate_name in candidate_names:
        try:
            if importlib.util.find_spec(candidate_name) is not None:
                normalized_lib_name = candidate_name
                break
        except (ImportError, ModuleNotFoundError, ValueError):
            continue

    if normalized_lib_name is None:
        if not silent:
            raise ModuleNotFoundError(f"{lib_name} is not installed")
        return None

    return importlib.import_module(normalized_lib_name)

# --- INTERNAL TOOLS ---

def _normalize_lib_name(lib_name: str) -> str:
    """
    Normalize library-name input into a validated name.

    Args:
        lib_name (str): Library name to normalize.

    Returns:
        str: Validated library name.
    """

    if not isinstance(lib_name, str):
        raise TypeError("lib_name must be a string")

    cleaned_name = lib_name.strip()
    if not cleaned_name:
        raise ValueError("lib_name cannot be empty")
    return cleaned_name

#%% === Text Helpers ===

def str_normalize(
    text: str,
    lower: bool = False,
    valid_chars: str | set[str] | None = VAR["default_valid_chars"],
    engine: str | None = "Unidecode",
    ) -> str:
    """
    Normalize a string for matching and comparison.

    Args:
        text (str): Input string to normalize.
        lower (bool): Convert the output to lowercase when `True`.
        valid_chars (str | set[str] | None): Extra characters to preserve
            through transliteration and invalid-character filtering.
            `None` is treated the same as `""`.
        engine (str | None): Optional transliteration engine to apply before
            invalid-character filtering. `Unidecode` is tried by default when
            installed.

    Returns:
        str: Normalized string value.

    Raises:
        TypeError: Raised when `text` is not a string, when `valid_chars`
            is neither a string, a set, nor `None`, or when `engine` is
            neither a string nor `None`.
        ValueError: Raised when `engine` names an unsupported transliteration
            engine.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    normalized_text = text.strip()
    if not normalized_text:
        return ""

    valid_characters = _resolve_valid_characters(valid_chars)
    normalized_text = _transliterate_text(normalized_text, engine, valid_chars)

    normalized_characters: list[str] = []
    for character in normalized_text:
        if character in valid_characters:
            normalized_characters.append(character)
            continue

        normalized_character = character.casefold() if lower else character
        for decomposed_character in unicodedata.normalize("NFKD", normalized_character):
            if unicodedata.combining(decomposed_character):
                continue
            if decomposed_character.isalnum() or decomposed_character in valid_characters:
                normalized_characters.append(decomposed_character)
                continue
            normalized_characters.append(" ")

    normalized_text = "".join(normalized_characters)
    return re.sub(r"\s+", " ", normalized_text).strip()


def str2float(
    value: object,
    si_format: bool | None = None,
    silent: bool = False,
    ) -> float | None:
    """
    Convert a supported value to a finite float.

    Args:
        value (object): Value to convert.
        si_format (bool | None): Force the numeric format when provided.
            `True` uses `,` for thousands and `.` for decimals. `False`
            uses `.` for thousands and `,` for decimals. `None` enables
            automatic format detection. In auto-detect mode, a single `.`
            is treated as a decimal separator, while a single `,` may be
            interpreted as either a decimal or thousands separator based on
            the grouped-digit heuristic.
        silent (bool): Return `None` instead of raising `ValueError` for
            invalid or non-finite numeric inputs when `True`. Defaults to
            `False`.

    Returns:
        float | None: Parsed float value, or `None` when conversion is not
            possible.

    Raises:
        ValueError: Raised when the input is non-finite, looks numeric but
            uses an invalid separator pattern, or conflicts with a forced
            `si_format`, when `silent=False`.

    Notes:
        In auto-detect mode, a single `.` is always treated as a decimal
        separator.
        A single `,` may be treated as a decimal or thousands separator
        based on the grouped-digit heuristic.
        Leading decimal values such as `.053` are accepted and treated as
        `0.053`.
        Scientific notation such as `1e3` is supported.
    """

    # --- SETUP AND VALIDATION ---
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        numeric_value = float(value)
        if not _is_valid_number(numeric_value):
            return _raise_or_none("Non-finite numeric input", silent, ValueError)
        return numeric_value

    if not isinstance(value, str):
        return None

    cleaned_value = value.strip()
    if not cleaned_value:
        return None
    cleaned_value = re.sub(r"\s+", "", cleaned_value)
    if not cleaned_value:
        return None

    if _is_non_finite_numeric_string(cleaned_value):
        return _raise_or_none("Non-finite numeric input", silent, ValueError)
    lowered_value = cleaned_value.lower()

    # --- FORMAT DETECTION ---
    mantissa_value = lowered_value.partition("e")[0]
    thousands_sep, decimal_sep = "", "."
    has_comma = "," in mantissa_value
    has_dot = "." in mantissa_value
    exponent_pattern = r"(?:[eE][+-]?\d+)?"
    numeric_like = bool(re.fullmatch(r"[+-]?[\d.,]+(?:[eE][+-]?\d*)?", cleaned_value))

    if si_format is True:
        thousands_sep, decimal_sep = ",", "."
    elif si_format is False:
        thousands_sep, decimal_sep = ".", ","
    elif has_comma and has_dot:
        if mantissa_value.rfind(".") > mantissa_value.rfind(","):
            thousands_sep, decimal_sep = ",", "."
        else:
            thousands_sep, decimal_sep = ".", ","
    elif has_dot:
        if mantissa_value.count(".") > 1:
            thousands_sep, decimal_sep = ".", ","
    elif has_comma:
        if mantissa_value.count(",") > 1:
            thousands_sep, decimal_sep = ",", "."
        else:
            integer_part, decimal_part = mantissa_value.rsplit(",", maxsplit=1)
            if (
                len(decimal_part) == 3
                and 1 <= len(integer_part.lstrip("+-")) <= 3
                and integer_part.lstrip("+-").isdigit()
            ):
                thousands_sep, decimal_sep = ",", "."
            else:
                thousands_sep, decimal_sep = "", ","

    # --- PATTERN VALIDATION ---
    si_pattern = (
        rf"^[+-]?(?:(?:\d{{1,3}}(?:,\d{{3}})+|\d+)(?:\.\d+)?|\.\d+)"
        rf"{exponent_pattern}$"
    )
    non_si_pattern = (
        rf"^[+-]?(?:(?:\d{{1,3}}(?:\.\d{{3}})+|\d+)(?:,\d+)?|,\d+)"
        rf"{exponent_pattern}$"
    )
    decimal_fragment_pattern = rf"{re.escape(decimal_sep)}\d+"

    if thousands_sep:
        grouped_integer_pattern = rf"(?:\d{{1,3}}(?:{re.escape(thousands_sep)}\d{{3}})+|\d+)"
        float_pattern = (
            rf"^[+-]?(?:"
            rf"{grouped_integer_pattern}(?:{decimal_fragment_pattern})?"
            rf"|{decimal_fragment_pattern}"
            rf"){exponent_pattern}$"
        )
    else:
        float_pattern = (
            rf"^[+-]?(?:\d+(?:{decimal_fragment_pattern})?|{decimal_fragment_pattern})"
            rf"{exponent_pattern}$"
        )

    if not re.fullmatch(float_pattern, cleaned_value):
        if not numeric_like:
            return None

        if si_format is True and re.fullmatch(non_si_pattern, cleaned_value):
            return _raise_or_none("Input format conflicts with si_format=True", silent, ValueError)
        if si_format is False and re.fullmatch(si_pattern, cleaned_value):
            return _raise_or_none("Input format conflicts with si_format=False", silent, ValueError)

        return _raise_or_none(f"Invalid numeric format: {cleaned_value}", silent, ValueError)

    # --- NORMALIZATION AND RETURN ---
    normalized_value = cleaned_value
    if thousands_sep:
        normalized_value = normalized_value.replace(thousands_sep, "")
    if decimal_sep != ".":
        normalized_value = normalized_value.replace(decimal_sep, ".")

    parsed_value = float(normalized_value)
    if not _is_valid_number(parsed_value):
        return _raise_or_none("Non-finite numeric input", silent, ValueError)

    return parsed_value


def abbr2number(
    value: object,
    suffix_factors: dict[str, int | float] | None = None,
    silent: bool = True,
    ) -> int | float | None:
    """
    Convert a compact number string such as `1M` into a numeric value.

    Args:
        value (object): Value to convert.
        suffix_factors (dict[str, int | float] | None): Suffix-to-multiplier
            map. Defaults to `VAR["number_suffix_factors"]`.
        silent (bool): Return `None` instead of raising `ValueError` for
            invalid compact number inputs when `True`. Defaults to `True`.

    Returns:
        int | float | None: Expanded numeric value, or `None` when
            conversion is not possible.

    Raises:
        TypeError: Raised when `suffix_factors` is not a dictionary of
            alphabetic string keys and numeric multipliers, when
            `silent=False`.
        ValueError: Raised when the input is empty, unsupported,
            non-finite, contains an invalid compact-number suffix, or
            uses non-positive or non-finite suffix multipliers, or maps
            the empty-string suffix to a value other than `1`, when
            `silent=False`.

    Notes:
        Suffix matching is case-sensitive.
        Explicit custom suffix keys must contain only letters, except for
        the empty-string suffix used for plain units.
    """

    # --- SETUP AND VALIDATION ---
    if value is None:
        return _raise_or_none("Abbreviated number input cannot be None", silent, ValueError)
    if isinstance(value, bool):
        return _raise_or_none("Boolean input is not a valid abbreviated number", silent, ValueError)

    if isinstance(value, (int, float)):
        numeric_value = float(value)
        if not _is_valid_number(numeric_value):
            return _raise_or_none("Non-finite numeric input", silent, ValueError)
        return int(numeric_value) if numeric_value.is_integer() else numeric_value

    if not isinstance(value, str):
        return _raise_or_none(f"Unsupported abbreviated number input type: {type(value).__name__}", silent, ValueError)

    cleaned_value = value.strip()
    if not cleaned_value:
        return _raise_or_none("Abbreviated number input cannot be empty", silent, ValueError)
    if _is_non_finite_numeric_string(cleaned_value):
        return _raise_or_none("Non-finite numeric input", silent, ValueError)

    resolved_suffix_factors = _resolve_suffix_factors(suffix_factors, silent=silent)
    if resolved_suffix_factors is None:
        return None

    # --- PARSING ---
    for suffix, multiplier in _sorted_suffix_items_for_parsing(resolved_suffix_factors):
        if not cleaned_value.endswith(suffix):
            continue

        base_value = cleaned_value[:-len(suffix)].strip()
        parsed_base_value = str2float(base_value, silent=silent)
        if parsed_base_value is None:
            return _raise_or_none(f"Invalid abbreviated number: {cleaned_value}", silent, ValueError)

        expanded_value = parsed_base_value * multiplier
        if not _is_valid_number(expanded_value):
            return _raise_or_none("Non-finite numeric input", silent, ValueError)

        return int(expanded_value) if expanded_value.is_integer() else expanded_value

    parsed_value = str2float(cleaned_value, silent=True)
    if parsed_value is not None:
        return int(parsed_value) if parsed_value.is_integer() else parsed_value

    return _raise_or_none(f"Invalid abbreviated number: {cleaned_value}", silent, ValueError)


def number2abbr(
    value: object,
    suffix_factors: dict[str, int | float] | None = None,
    decimals: int = 2,
    silent: bool = True,
    ) -> str | None:
    """
    Convert a numeric value into compact suffix notation such as `1M`.

    Args:
        value (object): Value to format.
        suffix_factors (dict[str, int | float] | None): Suffix-to-multiplier
            map. Defaults to `VAR["number_suffix_factors"]`.
        decimals (int): Maximum decimal places to keep. Defaults to `2`.
        silent (bool): Return `None` instead of raising `ValueError` for
            invalid inputs when `True`. Defaults to `True`.

    Returns:
        str | None: Compact string representation, or `None` when
            conversion is not possible.

    Raises:
        TypeError: Raised when `decimals` is not an integer or
            `suffix_factors` is not a dictionary of alphabetic string keys
            and numeric multipliers.
        ValueError: Raised when `decimals` is negative, the input is
            non-finite, the suffix multipliers are non-positive or
            non-finite, the empty-string suffix maps to a value other
            than `1`, or multiple suffixes share the same multiplier.

    Notes:
        Negative values are accepted and keep their sign in the output.
        Suffix keys are case-sensitive.
        Explicit custom suffix keys must contain only letters, except for
        the empty-string suffix used for plain units.
    """

    # --- SETUP AND VALIDATION ---
    if isinstance(decimals, bool) or not isinstance(decimals, int):
        raise TypeError("decimals must be an integer")
    if decimals < 0:
        raise ValueError("decimals must be >= 0")
    if isinstance(value, str) and _is_non_finite_numeric_string(value):
        return _raise_or_none("Non-finite numeric input", silent, ValueError)

    resolved_suffix_factors = _resolve_suffix_factors(suffix_factors, silent=silent, unique=True)
    if resolved_suffix_factors is None:
        return None
    parsed_value = str2float(value, silent=True)

    if parsed_value is None:
        parsed_value = abbr2number(value, suffix_factors=resolved_suffix_factors, silent=True)
    if parsed_value is None:
        return _raise_or_none(f"Invalid numeric value: {value}", silent, ValueError)

    numeric_value = float(parsed_value)
    if not _is_valid_number(numeric_value):
        return _raise_or_none("Non-finite numeric input", silent, ValueError)

    # --- NORMALIZATION AND RETURN ---
    absolute_value = abs(numeric_value)

    suffix, multiplier = _select_suffix_for_number(absolute_value, resolved_suffix_factors)
    compact_value = absolute_value / multiplier

    next_suffix_items = sorted(
        (
            (candidate_suffix, candidate_multiplier)
            for candidate_suffix, candidate_multiplier in resolved_suffix_factors.items()
            if candidate_multiplier > multiplier
        ),
        key=lambda item: item[1],
    )
    for next_suffix, next_multiplier in next_suffix_items:
        rounded_compact_value = float(f"{compact_value:.{decimals}f}")
        rollover_threshold = next_multiplier / multiplier
        if (
            rounded_compact_value < rollover_threshold
            and not math.isclose(rounded_compact_value, rollover_threshold)
        ):
            break
        suffix, multiplier = next_suffix, next_multiplier
        compact_value = absolute_value / multiplier

    formatted_value = f"{compact_value:.{decimals}f}".rstrip("0").rstrip(".")
    if not formatted_value:
        formatted_value = "0"
    sign = "-" if numeric_value < 0 and formatted_value != "0" else ""
    return f"{sign}{formatted_value}{suffix}"


def str2bool(value: object, silent: bool = True) -> bool | None:
    """
    Convert a supported value to a boolean.

    Args:
        value (object): Value to convert.
        silent (bool): Return `None` instead of raising `ValueError` for
            invalid or unsupported boolean inputs when `True`. Defaults to
            `True`.

    Returns:
        bool | None: Parsed boolean value, or `None` when conversion is not
            possible.

    Raises:
        ValueError: Raised when the input is unsupported or cannot be parsed
            as a boolean, when `silent=False`.

    Notes:
        Boolean values are returned unchanged.
        Numeric inputs are accepted only for `0`, `1`, `0.0`, and `1.0`.
    """

    # --- SETUP AND VALIDATION ---
    if value is None:
        return _raise_or_none("Boolean input cannot be None", silent, ValueError)

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        if value in {0, 1}:
            return bool(value)
        return _raise_or_none("Numeric boolean input must be 0 or 1", silent, ValueError)

    if not isinstance(value, str):
        return _raise_or_none(f"Unsupported boolean input type: {type(value).__name__}", silent, ValueError)

    cleaned_value = value.strip()
    if not cleaned_value:
        return _raise_or_none("Boolean input cannot be empty", silent, ValueError)

    # --- NORMALIZATION AND RETURN ---
    parsed_numeric_value = str2float(cleaned_value, silent=True)
    if parsed_numeric_value is not None and parsed_numeric_value in {0, 1}:
        cleaned_value = str(int(parsed_numeric_value))
    
    normalized_value = cleaned_value.lower()
    if normalized_value in VAR["truthy_values"]:
        return True
    if normalized_value in VAR["falsy_values"]:
        return False

    return _raise_or_none(f"Invalid boolean value: {cleaned_value}", silent, ValueError)

# --- INTERNAL TOOLS ---

def _resolve_suffix_factors(
    suffix_factors: dict[str, int | float] | None,
    silent: bool = False,
    unique: bool = False,
) -> dict[str, int | float] | None:
    """
    Return the compact-number suffix factors to use.

    Args:
        suffix_factors (dict[str, int | float] | None): Optional explicit
            suffix map.
        silent (bool): Return `None` instead of raising for invalid suffix
            maps when `True`.
        unique (bool): Require multiplier values to be unique when `True`.

    Returns:
        dict[str, int | float] | None: Normalized suffix factors dictionary,
            or `None` when validation fails in silent mode.

    Notes:
        Explicit custom suffix keys must contain only letters, except for
        the empty-string suffix used for plain units.
    """

    if not isinstance(unique, bool):
        return _raise_or_none("unique must be a boolean", silent, TypeError)

    source_suffix_factors = VAR["number_suffix_factors"]
    if suffix_factors is not None:
        if not isinstance(suffix_factors, dict):
            return _raise_or_none("suffix_factors must be a dictionary", silent, TypeError)
        source_suffix_factors = suffix_factors

    resolved_suffix_factors: dict[str, int | float] = {}
    seen_multipliers: set[int | float] = set()
    for key, multiplier in source_suffix_factors.items():
        if not isinstance(key, str):
            return _raise_or_none("suffix_factors keys must be strings", silent, TypeError)
        if key:
            if not key.isalpha():
                return _raise_or_none("suffix_factors keys must contain only letters", silent, ValueError)

        if not _is_valid_number(multiplier):
            if isinstance(multiplier, bool) or not isinstance(multiplier, (int, float)):
                return _raise_or_none("suffix_factors multipliers must be numeric", silent, TypeError)
            return _raise_or_none("suffix_factors multipliers must be finite", silent, ValueError)
        if multiplier <= 0:
            return _raise_or_none("suffix_factors multipliers must be > 0", silent, ValueError)
        if key == "" and multiplier != 1:
            return _raise_or_none("suffix_factors empty-string key must map to 1", silent, ValueError)
        if unique and multiplier in seen_multipliers:
            return _raise_or_none("suffix_factors multipliers must be unique", silent, ValueError)

        resolved_suffix_factors[key] = multiplier
        seen_multipliers.add(multiplier)

    return resolved_suffix_factors


def _sorted_suffix_items_for_parsing(
    suffix_factors: dict[str, int | float],
) -> list[tuple[str, int | float]]:
    """
    Return suffixes ordered for unambiguous abbreviated-number parsing.

    Args:
        suffix_factors (dict[str, int | float]): Suffix-to-multiplier map.

    Returns:
        list[tuple[str, int | float]]: Non-empty suffix entries, sorted by
            suffix length in descending order.
    """

    return sorted(
        (
            (suffix, multiplier)
            for suffix, multiplier in suffix_factors.items()
            if suffix
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )


def _select_suffix_for_number(
    absolute_value: float,
    suffix_factors: dict[str, int | float],
) -> tuple[str, int | float]:
    """
    Return the largest multiplier that keeps the compact value at least `1`.

    Args:
        absolute_value (float): Absolute numeric value to format.
        suffix_factors (dict[str, int | float]): Suffix-to-multiplier map.

    Returns:
        tuple[str, int | float]: Selected suffix and multiplier pair, or
            plain units when no suffix fits.
    """

    sorted_suffix_items = sorted(suffix_factors.items(), key=lambda item: item[1], reverse=True)

    for suffix, multiplier in sorted_suffix_items:
        if multiplier <= 0:
            continue
        if absolute_value >= multiplier:
            return suffix, multiplier

    return "", 1


def _resolve_valid_characters(valid_chars: str | set[str] | None) -> set[str]:
    """
    Normalize preserved-character input into a character set.

    Args:
        valid_chars (str | set[str] | None): Characters to preserve.

    Returns:
        set[str]: Preserved character set.

    Raises:
        TypeError: Raised when `valid_chars` is neither a string, a set,
            nor `None`, or when a set item is not a string.
    """

    if valid_chars is None:
        return set()
    if isinstance(valid_chars, str):
        return set(valid_chars)
    if isinstance(valid_chars, set):
        resolved_valid_characters: set[str] = set()
        for item in valid_chars:
            if not isinstance(item, str):
                raise TypeError("valid_chars set items must be strings")
            resolved_valid_characters.update(item)
        return resolved_valid_characters
    raise TypeError("valid_chars must be a string, set, or None")


def _transliterate_text(
    text: str,
    engine: str | None = "Unidecode",
    valid_chars: str | set[str] | None = None,
    ) -> str:
    """
    Return text transliterated through the selected optional engine.

    Args:
        text (str): Text to transliterate.
        engine (str | None): Transliteration engine name. Pass `None` to skip
            transliteration. Currently only `Unidecode` is supported.
        valid_chars (str | set[str] | None): Characters that must not be
            transliterated. `None` is treated the same as `""`.

    Returns:
        str: Transliterated text. Return the original text when
            transliteration is disabled or `Unidecode` is not installed.
            Characters present in `valid_chars` are preserved as-is.

    Raises:
        TypeError: Raised when `text` is not a string, when `valid_chars`
            is neither a string, a set, nor `None`, or when `engine` is
            neither a string nor `None`.
        ValueError: Raised when `engine` names an unsupported transliteration
            engine.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if engine is not None and not isinstance(engine, str):
        raise TypeError("engine must be a string or None")

    valid_characters = _resolve_valid_characters(valid_chars)

    match engine:
        case None:
            return text
        case str() as engine_name if engine_name.strip().casefold() == "unidecode":
            unidecode_module = import_lib("unidecode", silent=True)
            if unidecode_module is None:
                return text
            return "".join(
                character if character in valid_characters else unidecode_module.unidecode(character)
                for character in text
            )
        case _:
            raise ValueError(
                f"Unsupported normalization engine: {engine}. "
                "Supported engines: None, Unidecode"
            )



#%% === Matching Helpers ===

def match_terms_to_text(
    text: str,
    search_terms: list[str],
    normalize: bool = True,
    valid_chars: str | set[str] | None = None,
    silent: bool = True,
    ignore_terms: list[str] | str = "default",
) -> bool:
    """
    Return `True` when any candidate term matches the input text.

    Args:
        text (str): Input text to search.
        search_terms (list[str]): Candidate search terms.
        normalize (bool): Normalize text and terms before matching.
        valid_chars (str | set[str] | None): Characters to preserve during
            normalization.
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
        case_sensitive (bool): Match with case sensitivity when `True`.

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


#%% === General Internal Tools ===

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


def _is_non_finite_numeric_string(value: str) -> bool:
    """
    Return `True` when a string is a signed non-finite numeric token.

    Args:
        value (str): String value to inspect.

    Returns:
        bool: Whether the input is a non-finite numeric token.
    """

    cleaned_value = re.sub(r"\s+", "", value.strip())
    if not cleaned_value:
        return False
    return cleaned_value.lower().lstrip("+-") in {"nan", "inf", "infinity"}


def _is_valid_number(value: object) -> bool:
    """
    Return `True` when a value is a finite integer or float.

    Args:
        value (object): Value to inspect.

    Returns:
        bool: Whether the input is a finite numeric value.
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _raise_or_none(
    message: str,
    silent: bool,
    error_type: type[Exception],
    ) -> None:
    """
    Raise a parsing error or return `None` in silent mode.

    Args:
        message (str): Error message to use.
        silent (bool): Return `None` instead of raising when `True`.
        error_type (type[Exception]): Exception type to raise.

    Returns:
        None: Always returns `None` in silent mode.
    """
    if silent:
        return None
    raise error_type(message)


#%%
