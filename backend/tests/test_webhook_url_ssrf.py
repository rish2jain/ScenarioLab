"""Tests for webhook URL SSRF hardening."""

import pytest

from app.api_integrations.webhook_url import validate_webhook_url


def test_accepts_public_https(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.api_integrations.webhook_url.socket.getaddrinfo",
        lambda *a, **k: [(0, 0, 0, "", ("93.184.216.34", 443))],
    )
    assert validate_webhook_url("https://example.com/hooks") == "https://example.com/hooks"


@pytest.mark.parametrize(
    "url,resolver_ip,match",
    [
        # URL-shape rejects: public DNS so failure cannot be blamed on private resolve.
        ("ftp://example.com", "93.184.216.34", r"http:// or https://"),
        ("https://user:pass@example.com/h", "93.184.216.34", "credentials"),
        # Host / address rejects: private resolver retained for DNS-path coverage.
        ("https://localhost/hook", "127.0.0.1", "hostname is not allowed"),
        ("http://127.0.0.1/hook", "127.0.0.1", "blocked"),
        ("http://10.0.0.5/hook", "127.0.0.1", "blocked"),
        ("http://169.254.169.254/latest", "127.0.0.1", "blocked"),
        ("http://[::1]/hook", "127.0.0.1", "blocked"),
    ],
)
def test_rejects_unsafe_urls(url: str, resolver_ip: str, match: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.api_integrations.webhook_url.socket.getaddrinfo",
        lambda *a, **k: [(0, 0, 0, "", (resolver_ip, 80))],
    )
    with pytest.raises(ValueError, match=match):
        validate_webhook_url(url)


def test_rejects_dns_to_private(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.api_integrations.webhook_url.socket.getaddrinfo",
        lambda *a, **k: [(0, 0, 0, "", ("10.1.2.3", 443))],
    )
    with pytest.raises(ValueError, match="blocked"):
        validate_webhook_url("https://evil.example/hook")
