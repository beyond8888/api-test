from typing import Any


def first_error(errors: dict[str, Any]) -> str:
    """Return the first validation error message from a DRF serializer errors dict."""
    if not errors:
        return 'Invalid request'
    value = next(iter(errors.values()))
    if isinstance(value, list):
        return str(value[0])
    if isinstance(value, dict):
        return first_error(value)
    return str(value)
