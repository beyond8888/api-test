"""
Global DRF exception handler — converts all exceptions to:
    { "code": <int>, "data": <any>, "message": <str> }
"""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .api_response import (
    CODE_FORBIDDEN,
    CODE_GENERIC_ERROR,
    CODE_NOT_FOUND,
    CODE_RATE_LIMITED,
    CODE_UNAUTHORIZED,
    fail,
    server_error,
)

logger = logging.getLogger(__name__)

# Map DRF exception classes → (error_code, http_status, log_message)
_EXCEPTION_MAP = {
    exceptions.AuthenticationFailed:   (CODE_UNAUTHORIZED, None),
    exceptions.NotAuthenticated:       (CODE_UNAUTHORIZED, None),
    exceptions.PermissionDenied:       (CODE_FORBIDDEN, None),
    exceptions.NotFound:               (CODE_NOT_FOUND, None),
    exceptions.MethodNotAllowed:       (-405, None),
    exceptions.NotAcceptable:          (-406, None),
    exceptions.UnsupportedMediaType:   (-415, None),
    exceptions.Throttled:              (CODE_RATE_LIMITED, None),
    exceptions.ValidationError:        (-422, None),
    exceptions.ParseError:             (-400, None),
}


def unified_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    DRF custom exception handler.

    Catches:
      1. DRF built-in exceptions  → mapped to unified {code, data, message}
      2. Django Http404           → 404
      3. Django PermissionDenied  → 403
      4. All other unhandled      → 500 (with optional DEBUG detail)
    """
    # 1. Let DRF handle its own exceptions first
    response = exception_handler(exc, context)

    if response is not None:
        # Standard DRF exception
        return _handle_drf_exception(response, exc)

    # 2. Django's own Http404 (bypasses DRF's NotFound in some cases)
    if isinstance(exc, Http404):
        logger.warning('Http404: %s', exc)
        return fail(str(exc) or 'Not found', code=CODE_NOT_FOUND, status=404)

    # 3. Django's PermissionDenied
    if isinstance(exc, DjangoPermissionDenied):
        logger.warning('PermissionDenied: %s', exc)
        return fail(str(exc) or 'Permission denied', code=CODE_FORBIDDEN, status=403)

    # 4. Unexpected exception — log traceback, return generic 500
    logger.exception('Unhandled exception: %s', exc)
    return server_error('Internal server error')


def _handle_drf_exception(response: Response, exc: Exception) -> Response:
    """Convert DRF's default response into our unified format with fail()."""
    http_status = response.status_code
    handler_info = _EXCEPTION_MAP.get(type(exc))

    if handler_info is not None:
        code, override_status = handler_info
        if override_status is not None:
            http_status = override_status
    else:
        code = -http_status if http_status >= 400 else CODE_GENERIC_ERROR

    message = _extract_message(response.data, exc)
    # Preserve field-level detail for validation errors
    data = response.data if isinstance(response.data, dict) else None

    return fail(message, code=code, status=http_status, data=data)


def _extract_message(data: dict, exc: Exception) -> str:
    """Extract human-readable message from DRF error response data."""
    if isinstance(data, dict):
        # ValidationError: {'field': ['error1', 'error2'], ...}
        if isinstance(exc, exceptions.ValidationError):
            errors = []
            for field, msgs in data.items():
                if isinstance(msgs, list):
                    errors.append(f"{field}: {'; '.join(str(m) for m in msgs)}")
                else:
                    errors.append(f"{field}: {msgs}")
            return '; '.join(errors) if errors else str(exc)
        # Other exceptions: use 'detail' field if present
        if 'detail' in data:
            return str(data['detail'])
    # Fallback
    if isinstance(data, str):
        return data
    return str(exc)
