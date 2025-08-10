"""Load environment variables from .env files"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Union


class DotEnv:
    """Main class for loading and managing environment variables from .env files."""

    def __init__(
        self, dotenv_path: Optional[Union[str, Path]] = None, verbose: bool = False
    ):
        """Initialize DotEnv instance.

        Args:
            dotenv_path: Path to the .env file. If None, searches for .env in current directory.
            verbose: Whether to print verbose output.
        """
        self.dotenv_path = self._find_dotenv_path(dotenv_path)
        self.verbose = verbose
        self._values: Dict[str, str] = {}

    def _find_dotenv_path(
        self, dotenv_path: Optional[Union[str, Path]]
    ) -> Optional[Path]:
        """Find the .env file path."""
        if dotenv_path is None:
            # Search for .env file starting from current directory
            current_dir = Path.cwd()
            while current_dir != current_dir.parent:
                env_file = current_dir / ".env"
                if env_file.exists():
                    return env_file
                current_dir = current_dir.parent
            return None

        path = Path(dotenv_path)
        return path if path.exists() else None

    def _parse_line(self, line: str) -> Optional[tuple[str, str]]:
        """Parse a single line from .env file.

        Args:
            line: Line to parse

        Returns:
            Tuple of (key, value) or None if line should be ignored
        """
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            return None

        # Match KEY=VALUE pattern with optional quotes
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not match:
            return None

        key, value = match.groups()

        # Handle quoted values
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
            # Unescape common escape sequences
            value = (
                value.replace('\\"', '"')
                .replace("\\n", "\n")
                .replace("\\r", "\r")
                .replace("\\t", "\t")
            )
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        # Handle variable expansion ${VAR} or $VAR
        value = self._expand_variables(value)

        return key, value

    def _expand_variables(self, value: str) -> str:
        """Expand variables in the format ${VAR} or $VAR."""

        # Handle ${VAR} format
        def replace_braced(match):
            var_name = match.group(1)
            return os.environ.get(var_name, self._values.get(var_name, ""))

        value = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace_braced, value)

        # Handle $VAR format
        def replace_simple(match):
            var_name = match.group(1)
            return os.environ.get(var_name, self._values.get(var_name, ""))

        value = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", replace_simple, value)

        return value

    def load_dotenv(self, override: bool = False) -> bool:
        """Load environment variables from .env file.

        Args:
            override: Whether to override existing environment variables

        Returns:
            True if file was loaded successfully, False otherwise
        """
        if not self.dotenv_path:
            if self.verbose:
                print("No .env file found")
            return False

        try:
            with open(self.dotenv_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        parsed = self._parse_line(line)
                        if parsed:
                            key, value = parsed
                            self._values[key] = value

                            # Set in os.environ if not exists or override is True
                            if key not in os.environ or override:
                                os.environ[key] = value
                                if self.verbose:
                                    print(f"Set {key}={value}")
                            elif self.verbose:
                                print(f"Skipped {key} (already exists)")
                    except Exception as e:
                        if self.verbose:
                            print(f"Error parsing line {line_num}: {e}")

            if self.verbose:
                print(f"Loaded .env file: {self.dotenv_path}")
            return True

        except Exception as e:
            if self.verbose:
                print(f"Error loading .env file: {e}")
            return False

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a value from loaded environment variables.

        Args:
            key: Environment variable key
            default: Default value if key not found

        Returns:
            Value or default
        """
        return self._values.get(key, default)

    def set(self, key: str, value: str, override: bool = True) -> None:
        """Set an environment variable.

        Args:
            key: Environment variable key
            value: Environment variable value
            override: Whether to override existing values
        """
        if key not in os.environ or override:
            os.environ[key] = value
        self._values[key] = value

    def unset(self, key: str) -> None:
        """Unset an environment variable.

        Args:
            key: Environment variable key to unset
        """
        os.environ.pop(key, None)
        self._values.pop(key, None)

    def values(self) -> Dict[str, str]:
        """Get all loaded values as a dictionary."""
        return self._values.copy()


# Convenience functions
def load_dotenv(
    dotenv_path: Optional[Union[str, Path]] = None,
    override: bool = False,
    verbose: bool = False,
) -> bool:
    """Load environment variables from .env file.

    Args:
        dotenv_path: Path to .env file
        override: Whether to override existing environment variables
        verbose: Whether to print verbose output

    Returns:
        True if loaded successfully, False otherwise
    """
    dotenv = DotEnv(dotenv_path, verbose)
    return dotenv.load_dotenv(override)


def find_dotenv(filename: str = ".env", raise_error_if_not_found: bool = False) -> str:
    """Find a .env file by walking up directories.

    Args:
        filename: Name of the .env file to find
        raise_error_if_not_found: Whether to raise an error if file not found

    Returns:
        Path to the .env file

    Raises:
        IOError: If file not found and raise_error_if_not_found is True
    """
    current_dir = Path.cwd()
    while current_dir != current_dir.parent:
        env_file = current_dir / filename
        if env_file.exists():
            return str(env_file)
        current_dir = current_dir.parent

    if raise_error_if_not_found:
        raise IOError(f"Could not find {filename}")

    return ""


def get_key(dotenv_path: Union[str, Path], key_to_get: str) -> Optional[str]:
    """Get a specific key from a .env file without loading all variables.

    Args:
        dotenv_path: Path to .env file
        key_to_get: Key to retrieve

    Returns:
        Value of the key or None if not found
    """
    dotenv = DotEnv(dotenv_path)
    dotenv.load_dotenv()
    return dotenv.get(key_to_get)


def set_key(
    dotenv_path: Union[str, Path],
    key_to_set: str,
    value_to_set: str,
    quote_mode: str = "auto",
) -> tuple[bool, str, str]:
    """Set a key in a .env file.

    Args:
        dotenv_path: Path to .env file
        key_to_set: Key to set
        value_to_set: Value to set
        quote_mode: How to quote the value ("auto", "always", "never")

    Returns:
        Tuple of (success, key, value)
    """
    path = Path(dotenv_path)

    # Determine if we need quotes
    needs_quotes = quote_mode == "always" or (
        quote_mode == "auto"
        and (
            " " in value_to_set
            or "\n" in value_to_set
            or "\t" in value_to_set
            or value_to_set.startswith("#")
        )
    )

    if needs_quotes:
        # Escape quotes and newlines
        escaped_value = (
            value_to_set.replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        formatted_value = f'"{escaped_value}"'
    else:
        formatted_value = value_to_set

    line_to_add = f"{key_to_set}={formatted_value}\n"

    try:
        if path.exists():
            # Read existing content
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Check if key already exists
            key_found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key_to_set}="):
                    lines[i] = line_to_add
                    key_found = True
                    break

            if not key_found:
                lines.append(line_to_add)

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        else:
            # Create new file
            with open(path, "w", encoding="utf-8") as f:
                f.write(line_to_add)

        return True, key_to_set, value_to_set

    except Exception:
        return False, key_to_set, value_to_set


def unset_key(dotenv_path: Union[str, Path], key_to_unset: str) -> tuple[bool, str]:
    """Remove a key from a .env file.

    Args:
        dotenv_path: Path to .env file
        key_to_unset: Key to remove

    Returns:
        Tuple of (success, key)
    """
    path = Path(dotenv_path)

    if not path.exists():
        return False, key_to_unset

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Filter out the key
        new_lines = [
            line for line in lines if not line.strip().startswith(f"{key_to_unset}=")
        ]

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True, key_to_unset

    except Exception:
        return False, key_to_unset


# Main entry point for CLI usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        dotenv_path = sys.argv[1]
    else:
        dotenv_path = None

    success = load_dotenv(dotenv_path, verbose=True)
    if not success:
        sys.exit(1)
