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
        if token_lower == "--data-urlencode":
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


def handle_url(tokens: list[str], i: int, state: ParserState) -> int:
    """--url URL — curl accepts the target URL as an explicit option.

    Browsers / proxy tools frequently emit `curl --url '...'` instead of a
    bare positional URL argument.
    """
    if i + 1 < len(tokens):
        url = tokens[i + 1].strip()
        if not url:
            state.warnings.append("Empty --url value ignored")
        elif state.url:
            state.warnings.append(
                f"Multiple URLs in one command are not supported; "
                f"using first ({state.url!r}), ignoring {url!r}"
            )
        else:
            state.url = url
        return i + 2
    state.warnings.append("--url requires a value")
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


def handle_head(tokens: list[str], i: int, state: ParserState) -> int:
    """-I / --head : send a HEAD request."""
    state.method = "HEAD"
    return i + 1


def handle_user_agent(tokens: list[str], i: int, state: ParserState) -> int:
    """-A / --user-agent 'Mozilla/5.0 …' -> User-Agent header."""
    if i + 1 < len(tokens):
        state.headers["User-Agent"] = tokens[i + 1]
        return i + 2
    return i + 1


def handle_referer(tokens: list[str], i: int, state: ParserState) -> int:
    """-e / --referer URL -> Referer header."""
    if i + 1 < len(tokens):
        state.headers["Referer"] = tokens[i + 1]
        return i + 2
    return i + 1


def handle_json_data(tokens: list[str], i: int, state: ParserState) -> int:
    """--json '{"a":1}' (curl >= 7.82): --data-raw plus a JSON content type."""
    if i + 1 >= len(tokens):
        return i + 1
    raw = tokens[i + 1]
    if raw.startswith("@"):
        state.warnings.append(
            "--json with an @file payload is not supported; "
            "paste the JSON content instead"
        )
    else:
        state.raw_body = raw
        state.headers["Content-Type"] = "application/json"
        if state.method == "GET":
            state.method = "POST"
    return i + 2


def handle_oauth2_bearer(tokens: list[str], i: int, state: ParserState) -> int:
    """--oauth2-bearer TOKEN -> Authorization: Bearer <token>."""
    if i + 1 < len(tokens):
        state.headers["Authorization"] = f"Bearer {tokens[i + 1]}"
        return i + 2
    return i + 1


def handle_get_flag(tokens: list[str], i: int, state: ParserState) -> int:
    """-G / --get : curl moves the payload into the query string.

    Not supported here; warn so the user knows the body is kept as-is.
    """
    state.warnings.append(
        "Flag -G/--get ignored: turning the payload into query parameters is "
        "not supported; the data is still sent as the request body"
    )
    return i + 1


def handle_noop_bool(tokens: list[str], i: int, state: ParserState) -> int:
    """Boolean flags that carry no meaning for request building."""
    return i + 1


def _consume_noop_value(tokens: list[str], i: int, state: ParserState) -> int:
    """Advance past a value-taking flag.

    A registered value-taking flag REQUIRES a value in curl (curl errors out
    otherwise), so we consume the next token unless the command ends or the
    next token is clearly another flag. The URL heuristic deliberately plays no
    part here: files such as `-o response.json` must be consumed even though
    they resemble a bare host URL. Unknown flags never reach this helper — the
    parser reports them and never swallows the following token.
    """
    if i + 1 < len(tokens):
        nxt = tokens[i + 1]
        if nxt == "-" or not nxt.startswith("-"):
            return i + 2
    return i + 1


def handle_noop_value(tokens: list[str], i: int, state: ParserState) -> int:
    """Value-taking flags that carry no meaning for request building."""
    return _consume_noop_value(tokens, i, state)


def handle_unsupported_bool(tokens: list[str], i: int, state: ParserState) -> int:
    """Flags that would change the request if honoured, so warn loudly."""
    state.warnings.append(f"Flag {tokens[i]} ignored: not supported by this importer")
    return i + 1


def handle_unsupported_value(tokens: list[str], i: int, state: ParserState) -> int:
    """Value-taking flags that cannot be honoured (proxy, client certs…)."""
    state.warnings.append(f"Flag {tokens[i]} ignored: not supported by this importer")
    return _consume_noop_value(tokens, i, state)
