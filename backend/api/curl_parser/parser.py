"""Main curl parser: orchestrates tokenization, dispatch, and assembly."""

import re

from . import handlers
from .tokenizer import tokenize
from .types import CurlParsedResult, ParserState

# Flag -> (handler_fn, long_flag, consumes_next_token)
FLAG_MAP: dict[str, tuple] = {
    # Method
    "-X": (handlers.handle_method, True),
    "--request": (handlers.handle_method, True),
    # Headers
    "-H": (handlers.handle_header, True),
    "--header": (handlers.handle_header, True),
    # Data
    "-d": (handlers.handle_data, True),
    "--data": (handlers.handle_data, True),
    "--data-raw": (handlers.handle_data, True),
    "--data-binary": (handlers.handle_data, True),
    "--data-urlencode": (handlers.handle_data, True),
    # Form
    "-F": (handlers.handle_form, True),
    "--form": (handlers.handle_form, True),
    # Cookies
    "-b": (handlers.handle_cookie, True),
    "--cookie": (handlers.handle_cookie, True),
    # Auth
    "-u": (handlers.handle_user, True),
    "--user": (handlers.handle_user, True),
    # Booleans
    "--compressed": (handlers.handle_compressed, False),
    "-k": (handlers.handle_insecure, False),
    "--insecure": (handlers.handle_insecure, False),
    "-s": (handlers.handle_silent, False),
    "--silent": (handlers.handle_silent, False),
    "-S": (handlers.handle_silent, False),
    "--show-error": (handlers.handle_silent, False),
    "-L": (handlers.handle_location, False),
    "--location": (handlers.handle_location, False),
    "-g": (handlers.handle_globoff, False),
    "--globoff": (handlers.handle_globoff, False),
    "-v": (handlers.handle_verbose, False),
    "--verbose": (handlers.handle_verbose, False),
}

# Combined short boolean flags that can appear like -sSL or -kv
SHORT_BOOLEAN_FLAGS = {"k", "s", "l", "v"}


def _looks_like_url(token: str) -> bool:
    """Heuristic to decide whether a non-flag positional token is the URL.

    curl's URL argument may legitimately be:
      * a full URL with scheme            -> https://example.com/api
      * a Postman/Insomnia variable URL   -> {{baseUrl}}/api/path  or {{baseUrl}}
      * a path-only URL                    -> /api/path
      * a bare host (curl adds http://)    -> example.com  or  host:8080/path
    """
    if "://" in token:
        return True
    # Postman / Insomnia template variables, e.g. {{baseUrl}}/api
    if token.startswith("{{"):
        return True
    # Path-only URLs
    if token.startswith("/"):
        return True
    # Bare host without scheme: no spaces and a domain/port/path shape
    return " " not in token and bool(re.match(r"^[A-Za-z0-9._-]+(:[0-9]+)?(/.*)?$", token))


class CurlParser:
    def __init__(self, raw_curl: str):
        self.raw = raw_curl
        self.state = ParserState()

    def parse(self) -> CurlParsedResult:
        tokens = tokenize(self.raw)
        tokens = tokens[1:]  # Skip 'curl'

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("-"):
                i = self._dispatch_flag(tokens, i)
            else:
                # Positional URL argument
                if not self.state.url:
                    if _looks_like_url(token):
                        self.state.url = token
                    else:
                        self.state.warnings.append(f"Unexpected positional argument: {token}")
                else:
                    self.state.warnings.append(f"Unexpected positional argument: {token}")
                i += 1

        return self.state.to_result()

    def _dispatch_flag(self, tokens: list[str], i: int) -> int:
        token = tokens[i]

        # Exact match in FLAG_MAP
        if token in FLAG_MAP:
            handler, consumes_next = FLAG_MAP[token]
            return handler(tokens, i, self.state)

        # Combined short flags like -sSLv
        if token.startswith("-") and not token.startswith("--") and len(token) > 2:
            all_short = True
            for ch in token[1:]:
                if ch.lower() not in SHORT_BOOLEAN_FLAGS:
                    all_short = False
                    break
            if all_short:
                for ch in token[1:]:
                    flag = f"-{ch.lower()}"
                    if flag in FLAG_MAP:
                        handler, _ = FLAG_MAP[flag]
                        handler(tokens, i, self.state)
                return i + 1

        # -XPOST (method combined with flag)
        if token.startswith("-X") and len(token) > 2:
            method = token[2:].upper()
            if method:
                self.state.method = method
            return i + 1

        # Unknown flag
        self.state.warnings.append(f"Unrecognized flag: {token}")
        # Skip if next token looks like a value (doesn't start with -)
        if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
            return i + 2
        return i + 1
