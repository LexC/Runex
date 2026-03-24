""" README
Console output helpers for engine-level workflows.

Sections:
- shared print and log configuration
- terminal messaging helpers
- public singleton aliases
"""

from __future__ import annotations

__all__ = [
    "LPrint",
    "configure_logger",
    "critical",
    "dotted_line_fill",
    "error",
    "exit",
    "info",
    "lprint",
    "warning",
]

#%% === Libraries ===
import inspect
import logging
import os
import re
import shutil
import sys

from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import Any, TextIO

#%% === General Tools ===

# ---------- Variables ----------
def global_variables() -> dict[str, Any]:
    """
    Return shared configuration values used by engine print helpers.

    Returns:
        dict[str, Any]: Default print settings and supported log labels.
    """

    return {
        "default_end": "\n",
        "default_sep": " ",
        "ansi_reset": "\033[0m",
        "ansi_escape_pattern": re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]"),
        "level_labels": {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "CRITICAL",
        },
        "level_colors": {
            "DEBUG": "\033[35m",
            "INFO": "\033[32m",
            "WARNING": "\033[33m",
            "ERROR": "\033[31m",
            "CRITICAL": "\033[37;41m",
        },
    }


VAR = global_variables()
_MODULE_FILE = Path(__file__).resolve()


#%% === Messaging Helpers ===
class LPrint:
    """
    Print helper that standardizes console messages and optional file logging.

    Attributes:
        _log_file (Path | None): File used to store emitted messages.
    """

    def __init__(self, log_file: str | PathLike[str] | None = None) -> None:
        """
        Initialize one printer instance with an optional log file.

        Args:
            log_file (str | PathLike[str] | None): Initial log-file path.
        """

        self._log_file: Path | None = None
        self.configure_logger(log_file)

    def __call__(
        self,
        *values: object,
        sep: str | None = VAR["default_sep"],
        end: str | None = VAR["default_end"],
        file: TextIO | None = None,
        flush: bool = False,
        level: int | str | None = None,
        log: bool = True,
    ) -> None:
        """
        Print values to the terminal and optionally append them to the log file.

        Args:
            *values (object): Objects to print.
            sep (str | None): String inserted between values. `None` uses the
                standard print separator.
            end (str | None): String appended after the printed values. `None`
                uses the standard print terminator.
            file (TextIO | None): Output stream used for terminal display.
            flush (bool): Whether to flush the output stream.
            level (int | str | None): Optional standardized log level label.
            log (bool): Whether to append the message to the configured log
                file.
        """

        resolved_sep = self._resolve_print_token(sep, VAR["default_sep"], argument_name="sep")
        resolved_end = self._resolve_print_token(end, VAR["default_end"], argument_name="end")
        level_label, level_number = self._resolve_level(level)
        if not isinstance(log, bool):
            raise TypeError("log must be a boolean")

        message = resolved_sep.join(str(value) for value in values)
        output_text = self._format_message(message, level_label)
        output_stream = self._resolve_output_stream(file, level_number)
        display_text = self._colorize_message(output_text, level_label, output_stream)

        print(display_text, end=resolved_end, file=output_stream, flush=flush)
        if log:
            log_text = self._strip_ansi_codes(f"{output_text}{resolved_end}")
            self._append_to_log(log_text)

    def lprint(self, *values: object, **kwargs: Any) -> None:
        """
        Alias `__call__` to preserve `lprint.lprint(...)` usage.

        Args:
            *values (object): Objects to print.
            **kwargs (Any): Keyword arguments forwarded to `__call__`.
        """

        self(*values, **kwargs)

    def configure_logger(self, log_file: str | PathLike[str] | None = None) -> Path | None:
        """
        Configure the optional log file used by the printer.

        Args:
            log_file (str | PathLike[str] | None): File used to store emitted
                messages. Passing `None` or an empty string disables file
                logging.

        Returns:
            Path | None: Configured log-file path, or `None` when file logging
                is disabled.

        Raises:
            IsADirectoryError: Raised when `log_file` points to a directory.
        """

        if log_file is None or not str(log_file).strip():
            self._log_file = None
            return None

        resolved_log_file = Path(str(log_file).strip()).expanduser()
        if resolved_log_file.exists() and resolved_log_file.is_dir():
            raise IsADirectoryError(f"log_file must be a file path: {resolved_log_file}")

        resolved_log_file.parent.mkdir(parents=True, exist_ok=True)
        resolved_log_file.touch(exist_ok=True)
        self._log_file = resolved_log_file
        return resolved_log_file

    def info(
        self,
        *values: object,
        source: str | None = None,
        line: int | str | None = None,
        timestamp: str | None = None,
        sep: str | None = VAR["default_sep"],
        end: str | None = VAR["default_end"],
        file: TextIO | None = None,
        flush: bool = False,
        log: bool = True,
    ) -> None:
        """
        Print one info-style message using the block layout.

        Args:
            *values (object): Objects to print.
            source (str | None): Optional source label shown in the metadata
                line.
            line (int | str | None): Optional line marker shown beside the
                source label.
            timestamp (str | None): Optional timestamp shown at the right side
                of the metadata line.
            sep (str | None): String inserted between values.
            end (str | None): String appended after the printed block.
            file (TextIO | None): Output stream used for terminal display.
            flush (bool): Whether to flush the output stream.
            log (bool): Whether to append the block to the configured log file.
        """

        self._print_level_block(
            *values,
            level=logging.INFO,
            source=source,
            line=line,
            timestamp=timestamp,
            sep=sep,
            end=end,
            file=file,
            flush=flush,
            log=log,
        )

    def warning(
        self,
        *values: object,
        source: str | None = None,
        line: int | str | None = None,
        timestamp: str | None = None,
        sep: str | None = VAR["default_sep"],
        end: str | None = VAR["default_end"],
        file: TextIO | None = None,
        flush: bool = False,
        log: bool = True,
    ) -> None:
        """
        Print one warning-style message using the block layout.

        Args:
            *values (object): Objects to print.
            source (str | None): Optional source label shown in the metadata
                line.
            line (int | str | None): Optional line marker shown beside the
                source label.
            timestamp (str | None): Optional timestamp shown at the right side
                of the metadata line.
            sep (str | None): String inserted between values.
            end (str | None): String appended after the printed block.
            file (TextIO | None): Output stream used for terminal display.
            flush (bool): Whether to flush the output stream.
            log (bool): Whether to append the block to the configured log file.
        """

        self._print_level_block(
            *values,
            level=logging.WARNING,
            source=source,
            line=line,
            timestamp=timestamp,
            sep=sep,
            end=end,
            file=file,
            flush=flush,
            log=log,
        )

    def error(
        self,
        *values: object,
        source: str | None = None,
        line: int | str | None = None,
        timestamp: str | None = None,
        sep: str | None = VAR["default_sep"],
        end: str | None = VAR["default_end"],
        file: TextIO | None = None,
        flush: bool = False,
        log: bool = True,
    ) -> None:
        """
        Print one error-style message using the block layout.

        Args:
            *values (object): Objects to print.
            source (str | None): Optional source label shown in the metadata
                line.
            line (int | str | None): Optional line marker shown beside the
                source label.
            timestamp (str | None): Optional timestamp shown at the right side
                of the metadata line.
            sep (str | None): String inserted between values.
            end (str | None): String appended after the printed block.
            file (TextIO | None): Output stream used for terminal display.
            flush (bool): Whether to flush the output stream.
            log (bool): Whether to append the block to the configured log file.
        """

        self._print_level_block(
            *values,
            level=logging.ERROR,
            source=source,
            line=line,
            timestamp=timestamp,
            sep=sep,
            end=end,
            file=file,
            flush=flush,
            log=log,
        )

    def critical(
        self,
        *values: object,
        source: str | None = None,
        line: int | str | None = None,
        timestamp: str | None = None,
        sep: str | None = VAR["default_sep"],
        end: str | None = VAR["default_end"],
        file: TextIO | None = None,
        flush: bool = False,
        log: bool = True,
    ) -> None:
        """
        Print one critical-style message using the block layout.

        Args:
            *values (object): Objects to print.
            source (str | None): Optional source label shown in the metadata
                line.
            line (int | str | None): Optional line marker shown beside the
                source label.
            timestamp (str | None): Optional timestamp shown at the right side
                of the metadata line.
            sep (str | None): String inserted between values.
            end (str | None): String appended after the printed block.
            file (TextIO | None): Output stream used for terminal display.
            flush (bool): Whether to flush the output stream.
            log (bool): Whether to append the block to the configured log file.
        """

        self._print_level_block(
            *values,
            level=logging.CRITICAL,
            source=source,
            line=line,
            timestamp=timestamp,
            sep=sep,
            end=end,
            file=file,
            flush=flush,
            log=log,
        )

    def exit(self, message: str, exit_code: int = 1) -> None:
        """
        Print a critical message and exit the current process.

        Args:
            message (str): Error text to display before exiting.
            exit_code (int): Process exit code.
        """

        self.critical(f"{message}\n\nExiting the program.")
        sys.exit(exit_code)

    def dotted_line_fill(self, prefix: str, suffix: str, fill_char: str = ".") -> str:
        """
        Fill the current terminal width between two text fragments.

        Args:
            prefix (str): Leading text.
            suffix (str): Trailing text.
            fill_char (str): Single character used to fill the remaining width.

        Returns:
            str: Combined line padded with the requested fill character.

        Raises:
            ValueError: Raised when `fill_char` is not exactly one character.
        """

        if len(fill_char) != 1:
            raise ValueError("fill_char must be exactly one character")

        terminal_width = shutil.get_terminal_size(fallback=(80, 20)).columns
        dots_needed = max(0, terminal_width - len(prefix) - len(suffix))
        return f"{prefix}{fill_char * dots_needed}{suffix}"

    # ---------- Internal Tools ----------
    def _print_level_block(
        self,
        *values: object,
        level: int,
        source: str | None = None,
        line: int | str | None = None,
        timestamp: str | None = None,
        sep: str | None = VAR["default_sep"],
        end: str | None = VAR["default_end"],
        file: TextIO | None = None,
        flush: bool = False,
        log: bool = True,
    ) -> None:
        """
        Print one level-aware block message with metadata and borders.

        Args:
            *values (object): Objects to print.
            level (int): Logging level used for the block label and color.
            source (str | None): Optional source label shown in metadata.
            line (int | str | None): Optional line marker shown in metadata.
            timestamp (str | None): Optional timestamp shown in metadata.
            sep (str | None): String inserted between values.
            end (str | None): String appended after the printed block.
            file (TextIO | None): Output stream used for terminal display.
            flush (bool): Whether to flush the output stream.
            log (bool): Whether to append the block to the configured log file.
        """

        level_label, level_number = self._resolve_level(level)
        if level_label is None or level_number is None:
            raise ValueError("level block formatting requires a valid log level")
        if not isinstance(log, bool):
            raise TypeError("log must be a boolean")

        resolved_sep = self._resolve_print_token(sep, VAR["default_sep"], argument_name="sep")
        resolved_end = self._resolve_print_token(end, VAR["default_end"], argument_name="end")

        message = resolved_sep.join(str(value) for value in values)
        block_text = self._format_level_block(
            level_label,
            message,
            source=source,
            line=line,
            timestamp=timestamp,
        )
        output_stream = self._resolve_output_stream(file, level_number)
        display_text = self._colorize_block_boundaries(block_text, level_label, output_stream)

        print(display_text, end=resolved_end, file=output_stream, flush=flush)
        if log:
            log_text = self._strip_ansi_codes(f"{block_text}{resolved_end}")
            self._append_to_log(log_text)

    def _print_with_level(self, *values: object, level: int, **kwargs: Any) -> None:
        """
        Print one message with a fixed standardized level.

        Args:
            *values (object): Objects to print.
            level (int): Logging level used to format the message.
            **kwargs (Any): Keyword arguments forwarded to `__call__`.
        """

        if "log" in kwargs:
            raise TypeError("log can only be set when calling lprint() directly")

        self(*values, level=level, **kwargs)

    def _format_level_block(
        self,
        level_label: str,
        message: str,
        source: str | None = None,
        line: int | str | None = None,
        timestamp: str | None = None,
    ) -> str:
        """
        Format one block message with a title line, metadata, and body.

        Args:
            level_label (str): Label shown in the title line.
            message (str): Message body displayed inside the block.
            source (str | None): Optional source label shown in metadata.
            line (int | str | None): Optional line marker shown in metadata.
            timestamp (str | None): Optional timestamp shown in metadata.

        Returns:
            str: Fully formatted block text without a trailing terminator.
        """

        header_line = self._build_centered_level_line(level_label)
        footer_line = self.dotted_line_fill("", "", fill_char="-")
        metadata_line = self._format_block_metadata(source=source, line=line, timestamp=timestamp)

        return "\n".join([header_line, metadata_line, "", message, footer_line])

    def _build_centered_level_line(self, level_label: str) -> str:
        """
        Build one border line with the level label centered in the terminal.

        Args:
            level_label (str): Label shown in the title line.

        Returns:
            str: Centered title line sized to the current terminal width.
        """

        terminal_width = shutil.get_terminal_size(fallback=(80, 20)).columns
        centered_label = f" {level_label} "
        if len(centered_label) >= terminal_width:
            return centered_label
        return centered_label.center(terminal_width, "-")

    def _format_block_metadata(
        self,
        source: str | None = None,
        line: int | str | None = None,
        timestamp: str | None = None,
    ) -> str:
        """
        Format one metadata line for the block layout.

        Args:
            source (str | None): Optional source label shown on the left side.
            line (int | str | None): Optional line marker shown with the
                source.
            timestamp (str | None): Optional timestamp shown on the right side.

        Returns:
            str: Metadata line aligned to the current terminal width.
        """

        resolved_source, resolved_line = self._resolve_caller_location(stack_depth=1)
        if source is not None:
            resolved_source = source
        if line is not None:
            resolved_line = str(line)

        left_text = self._format_source_line(resolved_source, resolved_line)
        right_text = timestamp if timestamp is not None else datetime.now().strftime("%H:%M:%S")

        if left_text:
            return self.dotted_line_fill(f"{left_text} ", right_text, fill_char=" ")
        return self.dotted_line_fill("", right_text, fill_char=" ")

    def _format_source_line(self, source: str | None, line: str | None) -> str:
        """
        Format the source-and-line token for one metadata line.

        Args:
            source (str | None): Source label shown on the left side.
            line (str | None): Line marker shown beside the source label.

        Returns:
            str: Combined source token for the metadata line.
        """

        if source and line:
            return f"{source}:{line}"
        if source:
            return source
        if line:
            return line
        return ""

    def _resolve_caller_location(self, stack_depth: int = 0) -> tuple[str | None, str | None]:
        """
        Resolve the caller module name and line number for metadata output.

        Args:
            stack_depth (int): Minimum number of frames to walk upward from this
                helper before searching for the external caller.

        Returns:
            tuple[str | None, str | None]: Caller module stem and line number.
        """

        frame = inspect.currentframe()
        try:
            for _ in range(stack_depth):
                if frame is None:
                    return None, None
                frame = frame.f_back

            while frame is not None:
                frame_path = Path(frame.f_code.co_filename).resolve()
                if frame_path != _MODULE_FILE:
                    source = frame_path.stem
                    line = str(frame.f_lineno)
                    return source, line
                frame = frame.f_back

            return None, None
        finally:
            del frame

    def _resolve_level(self, level: int | str | None) -> tuple[str | None, int | None]:
        """
        Normalize one log level value into a display label and level number.

        Args:
            level (int | str | None): Logging level to normalize.

        Returns:
            tuple[str | None, int | None]: Display label and numeric level, or
                `(None, None)` for plain printing.

        Raises:
            TypeError: Raised when `level` is not an integer, string, or
                `None`.
            ValueError: Raised when `level` is an empty or unsupported string.
        """

        if level is None:
            return None, None

        if isinstance(level, str):
            normalized_level = level.strip().upper()
            if not normalized_level:
                raise ValueError("level cannot be empty")

            level_number = getattr(logging, normalized_level, None)
            if not isinstance(level_number, int):
                raise ValueError(f"Unsupported log level: {level}")
            level_label = VAR["level_labels"].get(level_number, normalized_level)
            return level_label, level_number

        if not isinstance(level, int):
            raise TypeError("level must be an int, string, or None")

        level_label = VAR["level_labels"].get(level)
        if level_label is not None:
            return level_label, level
        return f"LEVEL {level}", level

    def _resolve_print_token(self, value: str | None, default: str, argument_name: str) -> str:
        """
        Resolve one `print`-style separator or ending token.

        Args:
            value (str | None): Requested separator or terminator.
            default (str): Fallback token used when `value` is `None`.
            argument_name (str): Argument name used in error messages.

        Returns:
            str: Resolved separator or terminator.

        Raises:
            TypeError: Raised when `value` is not a string or `None`.
        """

        if value is None:
            return default
        if not isinstance(value, str):
            raise TypeError(f"{argument_name} must be a string or None")
        return value

    def _format_message(self, message: str, level_label: str | None) -> str:
        """
        Format one console message with an optional level label.

        Args:
            message (str): Message body to display.
            level_label (str | None): Optional standardized prefix label.

        Returns:
            str: Final message text ready for display and logging.
        """

        if level_label is None:
            return message
        if not message:
            return f"{level_label}:"
        return f"{level_label}: {message}"

    def _resolve_output_stream(self, file: TextIO | None, level_number: int | None) -> TextIO:
        """
        Resolve the output stream for one console message.

        Args:
            file (TextIO | None): Requested output stream.
            level_number (int | None): Numeric logging level for the message.

        Returns:
            TextIO: Stream used for console output.
        """

        if file is not None:
            return file

        if level_number is not None and level_number >= logging.WARNING:
            return sys.stderr
        return sys.stdout

    def _append_to_log(self, output_text: str) -> None:
        """
        Append text to the configured log file when logging is enabled.

        Args:
            output_text (str): Fully formatted text to append.
        """

        if self._log_file is None:
            return

        with self._log_file.open("a", encoding="utf-8") as file_obj:
            file_obj.write(output_text)

    def _strip_ansi_codes(self, text: str) -> str:
        """
        Remove ANSI escape sequences from one text string.

        Args:
            text (str): Text that may contain ANSI formatting codes.

        Returns:
            str: Plain text with ANSI escape sequences removed.
        """

        return VAR["ansi_escape_pattern"].sub("", text)

    def _supports_color(self, output_stream: TextIO) -> bool:
        """
        Return whether one output stream should receive ANSI color codes.

        Args:
            output_stream (TextIO): Stream used for console output.

        Returns:
            bool: `True` when ANSI colors should be emitted.
        """

        if os.getenv("NO_COLOR") is not None:
            return False

        if self._is_notebook_stream(output_stream):
            return True

        if os.getenv("TERM", "").lower() == "dumb":
            return False

        is_a_tty = getattr(output_stream, "isatty", None)
        return bool(callable(is_a_tty) and is_a_tty())

    def _colorize_block_boundaries(
        self,
        output_text: str,
        level_label: str,
        output_stream: TextIO,
    ) -> str:
        """
        Apply color only to the first and last lines of one block message.

        Args:
            output_text (str): Plain block text to display.
            level_label (str): Label used to select the border color.
            output_stream (TextIO): Stream used for console output.

        Returns:
            str: Block text with optional color on the border lines only.
        """

        if not self._supports_color(output_stream):
            return output_text

        color_code = VAR["level_colors"].get(level_label)
        if color_code is None:
            return output_text

        lines = output_text.split("\n")
        if not lines:
            return output_text

        lines[0] = f"{color_code}{lines[0]}{VAR['ansi_reset']}"
        if len(lines) > 1:
            lines[-1] = f"{color_code}{lines[-1]}{VAR['ansi_reset']}"
        return "\n".join(lines)

    def _is_notebook_stream(self, output_stream: TextIO) -> bool:
        """
        Return whether one output stream is backed by a notebook kernel.

        Args:
            output_stream (TextIO): Stream used for console output.

        Returns:
            bool: `True` when the stream is a notebook/IPython output stream.
        """

        stream_type = type(output_stream)
        return stream_type.__name__ == "OutStream" and stream_type.__module__.startswith("ipykernel.")

    def _colorize_message(
        self,
        output_text: str,
        level_label: str | None,
        output_stream: TextIO,
    ) -> str:
        """
        Apply ANSI color to one console message when supported.

        Args:
            output_text (str): Plain message text to display.
            level_label (str | None): Optional standardized prefix label.
            output_stream (TextIO): Stream used for console output.

        Returns:
            str: Message text with optional ANSI styling.
        """

        if level_label is None or not self._supports_color(output_stream):
            return output_text

        color_code = VAR["level_colors"].get(level_label)
        if color_code is None:
            return output_text
        return f"{color_code}{output_text}{VAR['ansi_reset']}"


#%% === Public Singleton Aliases ===
lprint = LPrint()
configure_logger = lprint.configure_logger
info = lprint.info
warning = lprint.warning
error = lprint.error
critical = lprint.critical
exit = lprint.exit
dotted_line_fill = lprint.dotted_line_fill
