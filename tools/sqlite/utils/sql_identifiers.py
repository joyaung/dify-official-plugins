import re

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def quote_identifier(name: str) -> str:
    """
    Validate a table or column name and return it quoted, so that it cannot
    terminate the surrounding statement and inject additional SQL.
    """
    if not isinstance(name, str) or not _IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'
