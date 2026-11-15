"""Trusted client IP resolution behind reverse proxies."""

from __future__ import annotations

import ipaddress

from typing import Protocol

from app.config import settings


class _IpRequest(Protocol):
    client: object | None
    headers: object


def _parse_networks(cidrs: list[str]) -> list[ipaddress._BaseNetwork]:
    networks: list[ipaddress._BaseNetwork] = []
    for raw in cidrs:
        raw = (raw or "").strip()
        if not raw:
            continue
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            continue
    return networks


def _peer_is_trusted_proxy(peer_host: str | None, trusted: list[ipaddress._BaseNetwork]) -> bool:
    if not peer_host or not trusted:
        return False
    try:
        peer = ipaddress.ip_address(peer_host)
    except ValueError:
        return False
    return any(peer in net for net in trusted)


def get_client_ip(request: _IpRequest) -> str:
    """
    Resolve the client IP for rate limiting.

  Only honors X-Forwarded-For / X-Real-IP when the immediate peer is listed in
  TRUSTED_PROXY_CIDRS. Otherwise uses request.client.host (anti-spoofing).
    """
    peer = request.client.host if request.client else None
    trusted = _parse_networks(settings.TRUSTED_PROXY_CIDRS)

    if _peer_is_trusted_proxy(peer, trusted):
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            # Left-most is the original client per common convention.
            candidate = xff.split(",")[0].strip()
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                pass
        real_ip = request.headers.get("X-Real-IP", "").strip()
        if real_ip:
            try:
                ipaddress.ip_address(real_ip)
                return real_ip
            except ValueError:
                pass

    if peer:
        return peer
    return "unknown"