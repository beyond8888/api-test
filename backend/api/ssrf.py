"""
SSRF (Server-Side Request Forgery) protection helpers for the proxy service.

These helpers perform a "best-effort" synchronous validation of a URL before
it is passed to ``httpx``. Because ``httpx`` may re-resolve DNS at connection
time, this cannot fully prevent DNS-rebinding attacks by itself. For stronger
protection, combine this module with:

* a firewall that blocks egress from the app to internal networks,
* an external proxy / egress controller,
* and/or running the application in an isolated network namespace.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError

# Only plain HTTP/HTTPS are allowed through the browser proxy.
_ALLOWED_SCHEMES = {"http", "https"}

# Hostnames/regexes we never want to forward requests to.
_DEFAULT_HOST_BLOCKLIST = {
    "localhost",
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",  # AWS / GCP / Azure metadata service
    "100.100.100.200",  # Alibaba Cloud metadata service
}


class UnsafeUrlError(ValidationError):
    """Raised when a URL is rejected by SSRF checks."""

    pass


def _ip_from_literal(value: str):
    """Return an IPv4Address/IPv6Address if ``value`` is an IP literal, else None."""
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _is_private_or_reserved(ip: ipaddress._BaseAddress) -> bool:
    """Return True for loopback, link-local, private, multicast or reserved IPs."""
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_multicast
        or ip.is_reserved
        or getattr(ip, "is_global", False) is False
    )


def _hostname_blocked(hostname: str) -> bool:
    """Check hostname against the explicit blocklist (case-insensitive)."""
    lower = hostname.lower()
    for blocked in _DEFAULT_HOST_BLOCKLIST:
        if lower == blocked or lower.endswith(f".{blocked}"):
            return True
    # Reject AWS-style metadata hostnames such as 169-254-169-254.*
    return bool(re.fullmatch(r"169-254-169-[0-9]+.*", lower))


def assert_safe_target(url: str, allow_private: bool = None) -> tuple[str, list[str], str | None]:
    """
    Validate that ``url`` points to a safe target.

    Returns a tuple of ``(normalized_url, resolved_ips, chosen_ip)`` where
    ``chosen_ip`` is the pre-validated IP the caller should connect to (used to
    pin the connection and defeat DNS-rebinding).

    ``allow_private`` defaults to ``settings.API_PROXY_ALLOW_PRIVATE`` and
    controls whether loopback/private addresses are allowed (useful only for
    local development).

    Raises:
        UnsafeUrlError: if the URL scheme, host, or resolved IP is not allowed.
    """
    if allow_private is None:
        allow_private = getattr(settings, "API_PROXY_ALLOW_PRIVATE", False)

    try:
        parsed = urlparse(url)
    except Exception as exc:  # noqa: BLE001
        raise UnsafeUrlError(f"无法解析 URL: {exc}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"不支持的协议: {parsed.scheme}")

    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL 缺少主机名")

    host = host.strip().lower()
    if _hostname_blocked(host):
        raise UnsafeUrlError(f"主机名被禁止访问: {host}")

    # Reject username/password in URLs to avoid credential leakage / surprise.
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("URL 中不允许包含用户名或密码")

    resolved_ips: list[str] = []

    # Case 1: the host is an IP literal.
    ip_literal = _ip_from_literal(host)
    if ip_literal is not None:
        if not allow_private and _is_private_or_reserved(ip_literal):
            raise UnsafeUrlError(f"禁止访问内部地址: {host}")
        resolved_ips.append(str(ip_literal))
        return url, resolved_ips, str(ip_literal)

    # Case 2: the host is a hostname. Resolve it and validate every result.
    try:
        addrinfo = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"无法解析主机 {host}: {exc}") from exc

    for _, _, _, _, sockaddr in addrinfo:
        ip = _ip_from_literal(sockaddr[0])
        if ip is None:
            continue
        if not allow_private and _is_private_or_reserved(ip):
            raise UnsafeUrlError(f"主机 {host} 解析到内部地址 {ip}，禁止访问")
        resolved_ips.append(str(ip))

    if not resolved_ips:
        raise UnsafeUrlError(f"主机 {host} 没有可解析的 IP 地址")

    return url, list(set(resolved_ips)), list(set(resolved_ips))[0]


def assert_safe_redirect(base_url: str, location: str, allow_private: bool = None) -> tuple[str, list[str], str | None]:
    """
    Resolve a redirect ``location`` (possibly relative) against ``base_url`` and
    run the same SSRF checks.

    Returns ``(absolute_url, resolved_ips, chosen_ip)``.
    """
    from urllib.parse import urljoin

    absolute = urljoin(base_url, location)
    return assert_safe_target(absolute, allow_private=allow_private)
