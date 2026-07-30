"""Validate outbound webhook URLs to reduce SSRF risk."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata",
        "metadata.google.internal",
        "metadata.google.com",
    }
)


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_webhook_url(url: str) -> str:
    """Return ``url`` if safe for server-side POST; raise ValueError otherwise."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not contain credentials")
    host = parsed.hostname
    if not host:
        raise ValueError("URL must include a hostname")
    host_l = host.lower().rstrip(".")
    if host_l in _BLOCKED_HOSTNAMES or host_l.endswith(".localhost"):
        raise ValueError("URL hostname is not allowed")
    if host_l.endswith(".internal") or host_l.endswith(".local"):
        raise ValueError("URL hostname is not allowed")

    # Literal IP in hostname
    try:
        literal = ipaddress.ip_address(host_l)
    except ValueError:
        literal = None
    if literal is not None and _is_blocked_ip(literal):
        raise ValueError("URL resolves to a blocked address")

    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ValueError(f"URL hostname could not be resolved: {e}") from e

    if not infos:
        raise ValueError("URL hostname could not be resolved")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise ValueError("URL resolves to a blocked address")

    return url.strip()
