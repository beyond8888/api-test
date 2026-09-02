"""Handler functions for individual curl flags.

Each handler receives the token list, current index, and mutable state,
and returns the new index after consuming its tokens.
"""

from urllib.parse import unquote

from .types import ParserState

METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


def handle_method(tokens: list[str], i: int, state: ParserState) -> int:
    """-X / --request METHOD"""
    if i + 1 < len(tokens):
        method = tokens[i + 1].upper()
        if method in METHODS:
            state.method = method
        else:
            state.warnings.append(f"Unknown HTTP method: {method}")
            state.method = method
        return i + 2
    return i + 1


def handle_header(tokens: list[str], i: int, state: ParserState) -> int:
    """-H / --header 'Name: Value'"""
    if i + 1 < len(tokens):
        header_str = tokens[i + 1]
        if ":" in header_str:
            key, _, value = header_str.partition(":")
            key = key.strip()
            value = value.strip()
            if key:
                state.headers[key] = value
        else:
            state.warnings.append(f"Skipping malformed header: {header_str}")
        return i + 2
    return i + 1


def handle_data(tokens: list[str], i: int, state: ParserState) -> int:
    """--data / --data-raw / --data-binary / --data-urlencode VALUE"""
    if i + 1 < len(tokens):
        value = tokens[i + 1]
        token_lower = tokens[i].lower().rstrip("'\"")
        if token_lower in ("--data-urlencode", "--data-urlencode"):
            # data-urlencode: key=value format, append to form
            if "=" in value:
                k, _, v = value.partition("=")
                state.form_fields[unquote(k)] = unquote(v)
            if state.method == "GET":
                state.method = "POST"
        else:
            state.raw_body = value
            if state.method == "GET":
                state.method = "POST"
        return i + 2
    return i + 1


def handle_form(tokens: list[str], i: int, state: ParserState) -> int:
    """-F / --form 'name=value' or 'name=@filepath'"""
    if i + 1 < len(tokens):
        value = tokens[i + 1]
        if "=" in value:
            k, _, v = value.partition("=")
            state.form_fields[k] = v
        if state.method == "GET":
            state.method = "POST"
        return i + 2
    return i + 1


def handle_cookie(tokens: list[str], i: int, state: ParserState) -> int:
    """-b / --cookie 'name=value; name2=value2'"""
    if i + 1 < len(tokens):
        cookie_str = tokens[i + 1]
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, _, v = pair.partition("=")
                state.cookies[k.strip()] = v.strip()
        return i + 2
    return i + 1


def handle_user(tokens: list[str], i: int, state: ParserState) -> int:
    """-u / --user 'user:password'"""
    if i + 1 < len(tokens):
        cred = tokens[i + 1]
        if ":" in cred:
            user, _, pwd = cred.partition(":")
            import base64
            encoded = base64.b64encode(f"{user}:{pwd}".encode()).decode()
            state.headers["Authorization"] = f"Basic {encoded}"
            state.warnings.append("Detected -u flag; added Basic auth header")
        return i + 2
    return i + 1


def handle_compressed(tokens: list[str], i: int, state: ParserState) -> int:
    state.compressed = True
    return i + 1


def handle_insecure(tokens: list[str], i: int, state: ParserState) -> int:
    state.insecure = True
    return i + 1


def handle_silent(tokens: list[str], i: int, state: ParserState) -> int:
    return i + 1


def handle_verbose(tokens: list[str], i: int, state: ParserState) -> int:
    return i + 1


def handle_location(tokens: list[str], i: int, state: ParserState) -> int:
    return i + 1


def handle_globoff(tokens: list[str], i: int, state: ParserState) -> int:
    """-g / --globoff : disable URL globbing (no-op for request building)."""
    return i + 1
