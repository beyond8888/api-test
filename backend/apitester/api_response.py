"""
Unified API response helpers.

All endpoints should use these to return consistent:
    { "code": 0, "data": ..., "message": "ok" }
    { "code": <error_code>, "data": null, "message": "..." }

Error code convention
---------------------
*   0               → success
*   negative ints   → business errors (kept distinct from HTTP status)
*   -1  generic     → generic / validation failure  (HTTP 400)
*   -401            → unauthorized / invalid creds    (HTTP 401)
*   -403            → forbidden                       (HTTP 403)
*   -404            → resource not found              (HTTP 404)
*   -429            → rate limited                    (HTTP 429)
*   -500            → unexpected server error         (HTTP 500)

Frontends should branch on the HTTP status first, then consult ``code`` for
fine-grained messaging.
"""
from typing import Any

from rest_framework.response import Response

# Canonical business error codes (mirror on the frontend if consumed).
CODE_SUCCESS = 0
CODE_GENERIC_ERROR = -1
CODE_UNAUTHORIZED = -401
CODE_FORBIDDEN = -403
CODE_NOT_FOUND = -404
CODE_RATE_LIMITED = -429
CODE_SERVER_ERROR = -500


def success(data: Any = None, message: str = 'ok', status: int = 200) -> Response:
    """Return a successful response."""
    return Response(
        {'code': CODE_SUCCESS, 'data': data, 'message': message},
        status=status,
    )


def fail(message: str, code: int = CODE_GENERIC_ERROR, status: int = 400, data: Any = None) -> Response:
    """Return an error response."""
    return Response(
        {'code': code, 'data': data, 'message': message},
        status=status,
    )


def server_error(
    message: str = 'Internal server error',
    data: Any = None,
    status: int = 500,
) -> Response:
    """Return a 5xx-class response.

    ``status`` is accepted (default 500) so callers can map proxy/SSRF errors
    to more precise codes (e.g. 400 for blocked, 502 for upstream failure,
    504 for timeout) without triggering a ``TypeError``.
    """
    return fail(message, code=CODE_SERVER_ERROR, status=status, data=data)
