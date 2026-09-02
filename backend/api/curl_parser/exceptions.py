"""Custom exceptions for curl parsing."""


class CurlParseError(Exception):
    """Raised when curl command is malformed or unparseable."""
    pass


class NotACurlCommand(CurlParseError):
    """Command does not start with 'curl'."""
    pass
