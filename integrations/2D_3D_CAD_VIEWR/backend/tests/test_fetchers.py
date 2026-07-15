import ipaddress

import pytest

from apps.viewer.services.errors import SecurityError, ValidationError
from apps.viewer.services.fetchers import SourceFetcher


def test_source_fetcher_allows_public_addresses(monkeypatch):
    fetcher = SourceFetcher(timeout_seconds=1, max_download_bytes=128, allowed_schemes=("https",))

    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("8.8.8.8")},
    )

    fetcher._validate_url("https://example.com/file.pdf")


def test_source_fetcher_blocks_private_addresses_without_allowlist(monkeypatch):
    fetcher = SourceFetcher(timeout_seconds=1, max_download_bytes=128, allowed_schemes=("https",))

    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("127.0.0.1")},
    )

    with pytest.raises(SecurityError):
        fetcher._validate_url("https://localhost/file.pdf")


def test_source_fetcher_rejects_unsupported_scheme(monkeypatch):
    fetcher = SourceFetcher(timeout_seconds=1, max_download_bytes=128, allowed_schemes=("https",))
    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("8.8.8.8")},
    )

    with pytest.raises(ValidationError):
        fetcher._validate_url("ftp://example.com/file.pdf")


def test_source_fetcher_allows_internal_hostname_when_allowlisted(monkeypatch):
    fetcher = SourceFetcher(
        timeout_seconds=1,
        max_download_bytes=128,
        allowed_schemes=("https",),
        internal_host_allowlist=("fileserver.example.local",),
    )
    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("10.10.4.20")},
    )

    fetcher._validate_url("https://fileserver.example.local/file.pdf")


def test_source_fetcher_allows_internal_cidr_when_allowlisted(monkeypatch):
    fetcher = SourceFetcher(
        timeout_seconds=1,
        max_download_bytes=128,
        allowed_schemes=("https",),
        internal_cidr_allowlist=("10.10.0.0/16",),
    )
    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("10.10.4.20")},
    )

    fetcher._validate_url("https://fileserver.example.local/file.pdf")


def test_source_fetcher_blocks_internal_addresses_when_internal_urls_disabled(monkeypatch):
    fetcher = SourceFetcher(
        timeout_seconds=1,
        max_download_bytes=128,
        allowed_schemes=("https",),
        internal_urls_enabled=False,
        internal_host_allowlist=("fileserver.example.local",),
        internal_cidr_allowlist=("10.10.0.0/16",),
    )
    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("10.10.4.20")},
    )

    with pytest.raises(SecurityError, match="Internal URLs are disabled"):
        fetcher._validate_url("https://fileserver.example.local/file.pdf")
