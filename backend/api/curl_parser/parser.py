"""Main curl parser: orchestrates tokenization, dispatch, and assembly."""

from . import handlers
from .tokenizer import tokenize
from .types import CurlParsedResult, ParserState, looks_like_url

# Flag -> (handler_fn, consumes_next_token)
#
# The set is maintained against curl's stable long/short options and the
# commands commonly exported by browsers (Chrome "Copy as cURL"), API clients
# (Postman/Insomnia/Apifox) and proxy recorders (Charles/Burp/Fiddler).
#
# Categories:
#   * request-affecting  — turned into method/headers/body/auth
#   * unsupported        — warn and skip (e.g. upstream proxy, client certs)
#   * no-op              — silently absorbed (timeouts, output, http version…)
FLAG_MAP: dict[str, tuple] = {
    # ── Method ──
    "-X": (handlers.handle_method, True),
    "--request": (handlers.handle_method, True),
    "-I": (handlers.handle_head, False),
    "--head": (handlers.handle_head, False),
    # ── URL (explicit option form, e.g. `curl --url 'https://...'`) ──
    "--url": (handlers.handle_url, True),
    # ── Headers / request fields ──
    "-H": (handlers.handle_header, True),
    "--header": (handlers.handle_header, True),
    "-A": (handlers.handle_user_agent, True),
    "--user-agent": (handlers.handle_user_agent, True),
    "-e": (handlers.handle_referer, True),
    "--referer": (handlers.handle_referer, True),
    # ── Data / body ──
    "-d": (handlers.handle_data, True),
    "--data": (handlers.handle_data, True),
    "--data-raw": (handlers.handle_data, True),
    "--data-binary": (handlers.handle_data, True),
    "--data-urlencode": (handlers.handle_data, True),
    "--json": (handlers.handle_json_data, True),
    # ── Form ──
    "-F": (handlers.handle_form, True),
    "--form": (handlers.handle_form, True),
    # ── Cookies ──
    "-b": (handlers.handle_cookie, True),
    "--cookie": (handlers.handle_cookie, True),
    "-c": (handlers.handle_noop_value, True),
    "--cookie-jar": (handlers.handle_noop_value, True),
    # ── Auth ──
    "-u": (handlers.handle_user, True),
    "--user": (handlers.handle_user, True),
    "--oauth2-bearer": (handlers.handle_oauth2_bearer, True),
    # ── TLS / security ──
    "-k": (handlers.handle_insecure, False),
    "--insecure": (handlers.handle_insecure, False),
    "-E": (handlers.handle_unsupported_value, True),
    "--cert": (handlers.handle_unsupported_value, True),
    "--key": (handlers.handle_unsupported_value, True),
    "--cacert": (handlers.handle_unsupported_value, True),
    "--capath": (handlers.handle_unsupported_value, True),
    "--ciphers": (handlers.handle_noop_value, True),
    "--tls-max": (handlers.handle_noop_value, True),
    "--tlsv1.0": (handlers.handle_noop_bool, False),
    "--tlsv1.1": (handlers.handle_noop_bool, False),
    "--tlsv1.2": (handlers.handle_noop_bool, False),
    "--tlsv1.3": (handlers.handle_noop_bool, False),
    "--ssl-no-revoke": (handlers.handle_noop_bool, False),
    # ── Compression ──
    "--compressed": (handlers.handle_compressed, False),
    # ── Redirects ──
    "-L": (handlers.handle_location, False),
    "--location": (handlers.handle_location, False),
    "--location-trusted": (handlers.handle_noop_bool, False),
    # ── Transfer semantics we cannot honour ──
    "-f": (handlers.handle_noop_bool, False),
    "--fail": (handlers.handle_noop_bool, False),
    "--fail-with-body": (handlers.handle_noop_bool, False),
    "-G": (handlers.handle_get_flag, False),
    "--get": (handlers.handle_get_flag, False),
    "-T": (handlers.handle_unsupported_value, True),
    "--upload-file": (handlers.handle_unsupported_value, True),
    "--digest": (handlers.handle_unsupported_bool, False),
    "--ntlm": (handlers.handle_unsupported_bool, False),
    "--negotiate": (handlers.handle_unsupported_bool, False),
    "--anyauth": (handlers.handle_unsupported_bool, False),
    # ── Timeouts / retries / transfer tuning (no request impact) ──
    "-m": (handlers.handle_noop_value, True),
    "--max-time": (handlers.handle_noop_value, True),
    "--connect-timeout": (handlers.handle_noop_value, True),
    "--max-redirs": (handlers.handle_noop_value, True),
    "--retry": (handlers.handle_noop_value, True),
    "--retry-delay": (handlers.handle_noop_value, True),
    "--retry-max-time": (handlers.handle_noop_value, True),
    "--retry-all-errors": (handlers.handle_noop_bool, False),
    "--limit-rate": (handlers.handle_noop_value, True),
    "--rate": (handlers.handle_noop_value, True),
    "--max-filesize": (handlers.handle_noop_value, True),
    "--keepalive-time": (handlers.handle_noop_value, True),
    "--proto": (handlers.handle_noop_value, True),
    "--proto-redir": (handlers.handle_noop_value, True),
    "--noproxy": (handlers.handle_noop_value, True),
    "--proxy-insecure": (handlers.handle_noop_bool, False),
    # ── HTTP version selection (no request impact) ──
    "--http1.0": (handlers.handle_noop_bool, False),
    "--http1.1": (handlers.handle_noop_bool, False),
    "--http2": (handlers.handle_noop_bool, False),
    "--http2-prior-knowledge": (handlers.handle_noop_bool, False),
    "--http3": (handlers.handle_noop_bool, False),
    # ── Output / client-side behaviour (no request impact) ──
    "-i": (handlers.handle_noop_bool, False),
    "--include": (handlers.handle_noop_bool, False),
    "-O": (handlers.handle_noop_bool, False),
    "--remote-name": (handlers.handle_noop_bool, False),
    "-N": (handlers.handle_noop_bool, False),
    "--no-buffer": (handlers.handle_noop_bool, False),
    "--no-progress-meter": (handlers.handle_noop_bool, False),
    "--progress-bar": (handlers.handle_noop_bool, False),
    "-o": (handlers.handle_noop_value, True),
    "--output": (handlers.handle_noop_value, True),
    "-D": (handlers.handle_noop_value, True),
    "--dump-header": (handlers.handle_noop_value, True),
    "-w": (handlers.handle_noop_value, True),
    "--write-out": (handlers.handle_noop_value, True),
    "--trace": (handlers.handle_noop_value, True),
    "--trace-ascii": (handlers.handle_noop_value, True),
    # ── Silent / verbose / globbing ──
    "-s": (handlers.handle_silent, False),
    "--silent": (handlers.handle_silent, False),
    "-S": (handlers.handle_silent, False),
    "--show-error": (handlers.handle_silent, False),
    "-v": (handlers.handle_verbose, False),
    "--verbose": (handlers.handle_verbose, False),
    "-g": (handlers.handle_globoff, False),
    "--globoff": (handlers.handle_globoff, False),
    # ── Upstream proxy (this platform does not relay through a proxy) ──
    "-x": (handlers.handle_unsupported_value, True),
    "--proxy": (handlers.handle_unsupported_value, True),
    "-U": (handlers.handle_unsupported_value, True),
    "--proxy-user": (handlers.handle_unsupported_value, True),
}

class CurlParser:
    def __init__(self, raw_curl: str):
        self.raw = raw_curl
        self.state = ParserState()

    def parse(self) -> CurlParsedResult:
        tokens = tokenize(self.raw)
        tokens = tokens[1:]  # Skip 'curl'

        # Normalize curl long-option `--flag=value` syntax into two tokens,
        # e.g. `--url=https://...` -> `--url` + `https://...`. Many tools
        # (Chrome, Postman, proxy recorders) emit this equals form.
        normalized: list[str] = []
        for tok in tokens:
            if tok.startswith("--") and "=" in tok:
                name, _, value = tok.partition("=")
                entry = FLAG_MAP.get(name)
                if entry is not None and entry[1] and value:
                    normalized.append(name)
                    normalized.append(value)
                    continue
            normalized.append(tok)
        tokens = normalized

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("-"):
                i = self._dispatch_flag(tokens, i)
            else:
                # Positional URL argument
                if not self.state.url:
                    if looks_like_url(token):
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

        # Combined short boolean flags like -sSLv, -sk, -sI (case-sensitive,
        # matching real curl: -I == --head, -i == --include).
        if token.startswith("-") and not token.startswith("--") and len(token) > 2:
            all_boolean = True
            for ch in token[1:]:
                entry = FLAG_MAP.get(f"-{ch}")
                if entry is None or entry[1]:
                    all_boolean = False
                    break
            if all_boolean:
                for ch in token[1:]:
                    handler, _ = FLAG_MAP[f"-{ch}"]
                    handler(tokens, i, self.state)
                return i + 1

        # -XPOST (method combined with flag)
        if token.startswith("-X") and len(token) > 2:
            method = token[2:].upper()
            if method:
                self.state.method = method
            return i + 1

        # Unknown flag. IMPORTANT: do NOT swallow the following token. The old
        # code skipped the next non-flag token, which silently dropped the URL
        # whenever an unrecognised flag preceded it (e.g. `curl -i URL`, or the
        # original `--url` bug). Values of genuinely unknown flags now surface
        # as harmless "Unexpected positional argument" warnings instead, and
        # the URL is never lost.
        self.state.warnings.append(f"Unrecognized flag: {token}")
        return i + 1
