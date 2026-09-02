import re
import shlex

from .exceptions import NotACurlCommand


def tokenize(raw_curl: str) -> list[str]:
    """
    Convert a raw curl command string into a list of tokens.

    Uses shlex for POSIX-compliant quoting, with pre-processing for
    common copy-paste artifacts from terminals and browsers.
    """
    if not raw_curl or not raw_curl.strip():
        raise NotACurlCommand("Empty input")

    s = raw_curl.strip()

    # Strip leading $ or > prompt markers (common when copying from terminal)
    s = re.sub(r'^[\$\>]\s*', '', s)

    # Convert smart/curly quotes to straight quotes
    s = s.replace('\u201c', '"').replace('\u201d', '"')  # left/right double
    s = s.replace('\u2018', "'").replace('\u2019', "'")  # left/right single

    # Normalize line continuations (backslash-newline -> space)
    s = s.replace('\\\n', ' ').replace('\\\r\n', ' ')

    try:
        tokens = shlex.split(s, posix=True)
    except ValueError as e:
        raise NotACurlCommand(f"Tokenization failed: {e}") from e

    if not tokens:
        raise NotACurlCommand("No tokens found")

    # Accept "curl" or full path like "/usr/bin/curl"
    first = tokens[0].lower()
    if not (first == "curl" or first.endswith("/curl") or first.endswith("\\curl")):
        raise NotACurlCommand(f"Command does not start with 'curl': {tokens[0]}")

    return tokens
