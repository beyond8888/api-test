import re
from typing import TypedDict


class CurlParsedResult(TypedDict, total=False):
    method: str
    url: str
    base_url: str
    path: str
    query_params: dict
    headers: dict
    body: dict | str | None
    raw_body: str | None
    body_type: str | None
    auth: dict | None
    cookies: dict
    form_fields: dict | None
    insecure: bool
    compressed: bool
    warnings: list[str]


def looks_like_url(token: str) -> bool:
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


class ParserState:
    """Mutable state accumulated during token-by-token parsing."""

    def __init__(self):
        self.method: str = "GET"
        self.url: str = ""
        self.headers: dict[str, str] = {}
        self.cookies: dict[str, str] = {}
        self.raw_body: str | None = None
        self.form_fields: dict[str, str] = {}
        self.insecure: bool = False
        self.compressed: bool = False
        self.warnings: list[str] = []

    def to_result(self) -> CurlParsedResult:
        from urllib.parse import parse_qs, urlparse

        parsed_url = urlparse(self.url) if self.url else None
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url and parsed_url.scheme else ""
        path = parsed_url.path if parsed_url else ""
        query_params = {}
        if parsed_url and parsed_url.query:
            for k, v in parse_qs(parsed_url.query, keep_blank_values=True).items():
                query_params[k] = v[0] if len(v) == 1 else v

        body: dict | str | None = None
        body_type: str | None = None

        if self.form_fields:
            body_type = "multipart"
            body = dict(self.form_fields)
        elif self.raw_body is not None:
            body_type = "raw"
            body = self.raw_body
            if self.headers.get("Content-Type", "").startswith("application/x-www-form-urlencoded"):
                body_type = "form"
                body = dict(p.split("=", 1) for p in self.raw_body.split("&") if "=" in p)
                if not body:
                    body = self.raw_body
            elif any(h.lower() == "content-type" and "json" in v.lower() for h, v in self.headers.items()):
                try:
                    import json
                    parsed = json.loads(self.raw_body)
                    body_type = "json"
                    body = parsed
                except (json.JSONDecodeError, ValueError):
                    pass

        auth: dict | None = None
        auth_header = ""
        for k, v in self.headers.items():
            if k.lower() == "authorization":
                auth_header = v
                break
        if auth_header.lower().startswith("bearer "):
            auth = {"type": "bearer", "token": auth_header[7:]}
        elif auth_header.lower().startswith("basic "):
            auth = {"type": "basic", "token": auth_header[6:]}

        return CurlParsedResult(
            method=self.method,
            url=self.url,
            base_url=base_url,
            path=path,
            query_params=query_params,
            headers=self.headers,
            body=body,
            raw_body=self.raw_body,
            body_type=body_type,
            auth=auth,
            cookies=self.cookies,
            form_fields=self.form_fields if self.form_fields else None,
            insecure=self.insecure,
            compressed=self.compressed,
            warnings=self.warnings,
        )
