from __future__ import annotations

"""Remote source fetching and URL safety checks for viewer inputs."""

import ipaddress
import socket
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests
from django.conf import settings

from apps.viewer.domain.types import FetchedSource
from apps.viewer.services.errors import FetchError, SecurityError, ValidationError


def _resolve_host_ips(hostname: str) -> set[ipaddress._BaseAddress]:
    addresses: set[ipaddress._BaseAddress] = set()
    for item in socket.getaddrinfo(hostname, None):
        ip = item[4][0]
        addresses.add(ipaddress.ip_address(ip))
    return addresses


def _is_blocked_ip(address: ipaddress._BaseAddress) -> bool:
    return any(
        [
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_reserved,
            address.is_multicast,
            address.is_unspecified,
        ]
    )


def _filename_from_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    name = PurePosixPath(parsed.path).name
    return name or "downloaded-file"


def _normalize_hostname(hostname: str) -> str:
    return hostname.rstrip(".").lower()


@dataclass(slots=True)
class SourceFetcher:
    timeout_seconds: int
    max_download_bytes: int
    allowed_schemes: tuple[str, ...]
    internal_urls_enabled: bool = True
    internal_host_allowlist: tuple[str, ...] = ()
    internal_cidr_allowlist: tuple[str, ...] = ()
    internal_networks: tuple[ipaddress._BaseNetwork, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # settings 由来の値を起動時に正規化し、fetch 時の分岐を単純にする。
        self.allowed_schemes = tuple(scheme.strip().lower() for scheme in self.allowed_schemes if scheme.strip())
        self.internal_host_allowlist = tuple(
            _normalize_hostname(hostname)
            for hostname in self.internal_host_allowlist
            if hostname.strip()
        )
        try:
            self.internal_networks = tuple(
                ipaddress.ip_network(cidr.strip(), strict=False)
                for cidr in self.internal_cidr_allowlist
                if cidr.strip()
            )
        except ValueError as exc:
            raise ValidationError(f"Invalid internal CIDR allowlist entry: {exc}") from exc

    def fetch(self, source_url: str) -> FetchedSource:
        # download より先に URL を検査し、危険な宛先へは通信しない。
        self._validate_url(source_url)
        try:
            response = requests.get(source_url, timeout=self.timeout_seconds, stream=True)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FetchError(f"Failed to fetch source URL: {exc}") from exc

        content = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            content.extend(chunk)
            # 一度に全量を抱えず stream しつつ、上限を超えた時点で止める。
            if len(content) > self.max_download_bytes:
                raise ValidationError("Downloaded file exceeds max size limit")

        mime_type = response.headers.get("Content-Type", "application/octet-stream").split(";")[0].strip().lower()
        filename = _filename_from_url(source_url)
        return FetchedSource(
            source_url=source_url,
            filename=filename,
            extension=filename.rsplit(".", 1)[-1].lower() if "." in filename else "",
            mime_type=mime_type,
            content=bytes(content),
        )

    def _validate_url(self, source_url: str) -> None:
        parsed = urlparse(source_url)
        if parsed.scheme.lower() not in self.allowed_schemes:
            raise ValidationError("Unsupported URL scheme")
        if not parsed.hostname:
            raise ValidationError("URL must include a hostname")

        hostname = _normalize_hostname(parsed.hostname)

        try:
            addresses = _resolve_host_ips(hostname)
        except socket.gaierror as exc:
            raise ValidationError(f"Hostname could not be resolved: {hostname}") from exc

        blocked_addresses = {address for address in addresses if _is_blocked_ip(address)}
        if not blocked_addresses:
            return
        if not self.internal_urls_enabled:
            raise SecurityError("Internal URLs are disabled")
        # internal URL は明示 allowlist 制にし、初心者でも「安全側が既定」だと分かるようにする。
        if hostname in self.internal_host_allowlist:
            return
        if blocked_addresses and all(
            any(address in network for network in self.internal_networks)
            for address in blocked_addresses
        ):
            return
        raise SecurityError("Internal URL is not allowed. Add the host or CIDR to the allowlist.")


def build_default_source_fetcher() -> SourceFetcher:
    return SourceFetcher(
        timeout_seconds=settings.VIEWER_TIMEOUT_SECONDS,
        max_download_bytes=settings.VIEWER_MAX_DOWNLOAD_BYTES,
        allowed_schemes=settings.VIEWER_ALLOWED_SCHEMES,
        internal_urls_enabled=settings.VIEWER_INTERNAL_URLS_ENABLED,
        internal_host_allowlist=settings.VIEWER_INTERNAL_HOST_ALLOWLIST,
        internal_cidr_allowlist=settings.VIEWER_INTERNAL_CIDR_ALLOWLIST,
    )
