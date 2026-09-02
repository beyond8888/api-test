"""
Mock execution engine — Python script sandbox + path matching.

Key design decisions:
 1. subprocess isolation — each script runs in a child Python process so
    misbehaving code (infinite loops, memory bombs) cannot take down Django.
 2. timeout via subprocess timeout — reliably kills runaway scripts.
 3. Path-param matching — converts template paths (api/users/<user_id>)
    into regex patterns and extracts named captures.
"""
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum script execution time (seconds)
SCRIPT_TIMEOUT = int(os.environ.get('MOCK_SCRIPT_TIMEOUT', '10'))

# Maximum response body size (bytes)
MAX_RESPONSE_SIZE = int(os.environ.get('MOCK_MAX_RESPONSE_SIZE', str(5 * 1024 * 1024)))

# --------------- safe request wrapper consumed by user scripts ---------------


def _normalise_querydict(qd: Any) -> Dict[str, Any]:
    """Convert a Django QueryDict (or any mapping) into a plain dict.

    Django's QueryDict returns a scalar for single-valued keys and a list
    for multi-valued keys. To make script behaviour predictable we:
      * drop the multi-value list when there's only one item
      * keep a list only when a key truly repeats
    """
    if qd is None:
        return {}
    if hasattr(qd, 'lists'):
        result: Dict[str, Any] = {}
        for key, values in qd.lists():
            result[key] = values[0] if len(values) == 1 else values
        return result
    # Already a plain dict / mapping
    return dict(qd)


class MockRequest:
    """Exposed to user scripts as the `request` object."""

    def __init__(
        self,
        method: str = 'GET',
        path: str = '/',
        query_params: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        body: str = '',
        path_params: Optional[Dict[str, str]] = None,
    ):
        self.method = method
        self.path = path
        # Normalise so scripts always see plain dict (scalar or list, never QueryDict)
        self.query_params: Dict[str, Any] = _normalise_querydict(query_params)
        self.headers = headers or {}
        self.body = body
        self.path_params = path_params or {}

    def param(self, name: str, default: Any = None) -> Any:
        """Look up a parameter from path_params first, then query_params.

        This lets scripts ignore whether the caller passed the value in the
        URL path or as a query string.
        """
        if name in self.path_params:
            return self.path_params[name]
        return self.query_params.get(name, default)

    def json(self) -> Any:
        """Parse request body as JSON."""
        try:
            return json.loads(self.body) if self.body else {}
        except json.JSONDecodeError:
            return {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'method': self.method,
            'path': self.path,
            'query_params': self.query_params,
            'headers': self.headers,
            'body': self.body,
            'path_params': self.path_params,
        }

    @classmethod
    def from_django(cls, request, mock_path: str, path_params: Dict[str, str]) -> 'MockRequest':
        """Build a MockRequest from a real Django/DRF request (used for live serving)."""
        method = request.method or 'GET'
        headers = {k: v for k, v in request.headers.items()}
        try:
            body = request.body.decode('utf-8', errors='replace')
        except Exception:
            body = ''
        return cls(
            method=method.upper(),
            path=mock_path,
            query_params=getattr(request, 'query_params', None),
            headers=headers,
            body=body,
            path_params=path_params,
        )


# --------------- path matching ---------------


def _path_to_regex(template: str) -> Tuple[re.Pattern, List[str]]:
    """Convert a template path like 'api/users/<user_id>/posts/<post_id>'
    into a compiled regex and a list of param names.

    Returns (regex, param_names).
    """
    param_names: List[str] = []
    # Replace <param> with named capture groups
    pattern = re.sub(
        r'<([^>]+)>',
        lambda m: (param_names.append(m.group(1)) or '(?P<' + re.escape(m.group(1)) + r'>[^/]+)'),
        re.escape(template),
    )
    # Strip leading/trailing slashes for consistency
    pattern = '^' + pattern.strip('/') + '$'
    return re.compile(pattern), param_names


def match_path(template: str, actual_path: str) -> Optional[Dict[str, str]]:
    """Match an actual request path against a template.

    Returns a dict of path_params on match, or None.
    """
    regex, _ = _path_to_regex(template)
    cleaned = actual_path.strip('/')
    m = regex.match(cleaned)
    if m:
        return {k: v for k, v in m.groupdict().items() if v is not None}
    return None


# --------------- sandboxed script execution ---------------


# Template used to execute the user script inside a subprocess.
# The user's script is injected, the `handle()` function is called,
# and the result is printed as JSON to stdout.
EXEC_TEMPLATE = '''
import json, sys, traceback
from types import SimpleNamespace

# --- user's script ---
__USER_SCRIPT_PLACEHOLDER__

# --- request wrapper exposed to the user script ---
class _Request:
    def __init__(self, data):
        self.method = data.get('method', 'GET')
        self.path = data.get('path', '/')
        # normalise query_params: scalar when single, list when repeated
        qp = data.get('query_params', {}) or {}
        if hasattr(qp, 'lists'):
            self.query_params = {k: (v[0] if len(v) == 1 else v) for k, v in qp.lists()}
        else:
            self.query_params = dict(qp)
        self.headers = data.get('headers', {}) or {}
        self.body = data.get('body', '') or ''
        self.path_params = data.get('path_params', {}) or {}

    def param(self, name, default=None):
        if name in self.path_params:
            return self.path_params[name]
        return self.query_params.get(name, default)

    def json(self):
        try:
            return json.loads(self.body) if self.body else {}
        except Exception:
            return {}

request = None
try:
    _raw = sys.argv[1] if len(sys.argv) > 1 else '{}'
    request = _Request(json.loads(_raw))
except Exception:
    request = _Request({})

# --- execute ---
try:
    result = handle(request)
    # The return value is treated as the response BODY by default, so users can
    # simply `return {...}` or `return 'text'` and the platform wraps it into the
    # final response (status_code=200 + JSON Content-Type) automatically.
    # Only when the returned dict explicitly contains a `status_code` or
    # `headers` key is it treated as a full response dict (backward compatible).
    if isinstance(result, dict) and ('status_code' in result or 'headers' in result):
        result.setdefault('status_code', 200)
        if not result.get('headers'):
            result['headers'] = {'Content-Type': 'application/json'}
        result.setdefault('body', '')
    else:
        result = {'status_code': 200, 'headers': {'Content-Type': 'application/json'}, 'body': result}

    # normalise body: convert non-string to JSON string
    if not isinstance(result.get('body'), str):
        result['body'] = json.dumps(result['body'], ensure_ascii=False, default=str)

    # limit response body size
    max_size = __MAX_SIZE_PLACEHOLDER__
    if len(result.get('body', '')) > max_size:
        result['body'] = result['body'][:max_size]
        result['__truncated'] = True

    print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False))
except Exception as e:
    tb = traceback.format_exc()
    print(json.dumps({'ok': False, 'error': str(e), 'traceback': tb}, ensure_ascii=False))
'''


def execute_script(script: str, request: MockRequest) -> Dict[str, Any]:
    """Execute a user-provided Python script in a sandboxed subprocess.

    Args:
        script: The Python source code (must define handle(request)).
        request: The incoming request context.

    Returns:
        A dict: { status_code: int, headers: dict, body: str }
    """
    if not script or not script.strip():
        return _default_response(request)

    # Dedent the user script so indentation in EXEC_TEMPLATE still works
    script = _safe_dedent(script)

    exec_code = (
        EXEC_TEMPLATE
        .replace('__USER_SCRIPT_PLACEHOLDER__', script)
        .replace('__MAX_SIZE_PLACEHOLDER__', str(MAX_RESPONSE_SIZE))
    )

    # Write to a temp file so we can run it
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, prefix='mock_') as f:
        f.write(exec_code)
        script_path = f.name

    try:
        start = time.monotonic()
        proc = subprocess.run(
            ['python3', script_path, json.dumps(request.to_dict(), ensure_ascii=False)],
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT,
            env={'PYTHONPATH': '', 'PATH': os.environ.get('PATH', '/usr/bin:/bin')},
        )
        elapsed = time.monotonic() - start

        logger.info('Mock script executed in %.3fs (exit=%d)', elapsed, proc.returncode)

        if proc.returncode != 0 or proc.stderr:
            stderr_preview = (proc.stderr or '')[:500]
            logger.warning('Mock script stderr: %s', stderr_preview)

        if not proc.stdout.strip():
            return {
                'status_code': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Script produced no output',
                    'stderr': (proc.stderr or '')[:1000],
                }),
            }

        try:
            output = json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            return {
                'status_code': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Script output is not valid JSON',
                    'raw_output': proc.stdout[:1000],
                }),
            }

        if not output.get('ok'):
            return {
                'status_code': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': output.get('error', 'Unknown script error'),
                    'traceback': output.get('traceback', ''),
                }),
            }

        return output['result']

    except subprocess.TimeoutExpired:
        logger.error('Mock script timed out after %ds', SCRIPT_TIMEOUT)
        return {
            'status_code': 504,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Script execution timed out after {SCRIPT_TIMEOUT}s'}),
        }
    except Exception as e:
        logger.exception('Mock script execution failed')
        return {
            'status_code': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Script execution error: {str(e)}'}),
        }
    finally:
        # Clean up temp file
        try:
            os.unlink(script_path)
        except OSError:
            pass


def _safe_dedent(code: str) -> str:
    """Dedent user code without choking on empty/whitespace-only strings."""
    import textwrap
    code = code.strip()
    if not code:
        return code
    return textwrap.dedent(code)


def _default_response(request: MockRequest) -> Dict[str, Any]:
    """Return a sensible default when no script is provided."""
    return {
        'status_code': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message': 'Mock endpoint (no script configured)',
            'method': request.method,
            'path': request.path,
        }),
    }
