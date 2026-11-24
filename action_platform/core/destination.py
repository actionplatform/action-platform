"""Where an authenticated request may go: the approved origin keeps the credential headers, a redirect anywhere else loses them, a pagination link anywhere else is refused, and — on the hosted platform — no request reaches a private or internal address the operator did not allow."""

from __future__ import annotations

import ipaddress
import socket
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Union

from action_platform.core.exception import ProviderError
from action_platform.core.origin import Origin, OriginError

Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
Address = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]

SAFE_HEADERS = frozenset({"accept", "user-agent"})


class DestinationError(ProviderError):
    pass


@dataclass(frozen=True)
class NetworkPolicy:
    """Which non-public addresses a request may reach. `enforce` False (the CLI, the MCP server) leaves the network alone; the hosted API and its workers enforce it from `AP_ALLOW_PRIVATE_NETWORKS`."""

    enforce: bool = False
    private: bool = False
    networks: tuple[Network, ...] = ()
    hosts: tuple[str, ...] = ()

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "NetworkPolicy":
        """`AP_ALLOW_PRIVATE_NETWORKS=1` admits private, loopback and unique-local ranges (never link-local, where cloud metadata lives); a comma-separated list of CIDR ranges and host names admits exactly those."""
        raw = env.get("AP_ALLOW_PRIVATE_NETWORKS", "").strip()

        if raw == "1":
            return cls(enforce=True, private=True)

        networks: list[Network] = []
        hosts: list[str] = []

        for item in (i.strip() for i in raw.split(",")):
            if not item:
                continue

            try:
                networks.append(ipaddress.ip_network(item, strict=False))
            except ValueError:
                hosts.append(item.lower().rstrip("."))

        return cls(enforce=True, networks=tuple(networks), hosts=tuple(hosts))

    def admits(self, address: Address) -> bool:
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped

        if any(address in n for n in self.networks):
            return True

        if address.is_link_local or address.is_multicast or address.is_unspecified:
            return False

        if address.is_global:
            return True

        return self.private and (address.is_private or address.is_loopback)

    def check(self, url: str) -> None:
        """Refuse `url` when its host resolves to an address this policy does not admit."""
        if not self.enforce:
            return

        try:
            origin = Origin.of(url)
        except OriginError as e:
            raise DestinationError(str(e)) from e

        if origin.host in self.hosts:
            return

        for address in _resolve(origin.host, origin.port):
            if not self.admits(address):
                raise DestinationError(
                    f"{origin.host} resolves to {address}, a private or internal address; "
                    "the operator allows such destinations with AP_ALLOW_PRIVATE_NETWORKS"
                )


def _resolve(host: str, port: int) -> list[Address]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return []

    return [ipaddress.ip_address(info[4][0].split("%", 1)[0]) for info in infos]


POLICY: list[NetworkPolicy] = [NetworkPolicy()]


def guard_networks(policy: NetworkPolicy) -> None:
    """Make `policy` the process's: the hosted API and its workers call it once on start."""
    POLICY[0] = policy


def network_policy() -> NetworkPolicy:
    return POLICY[0]


def same_origin(url: str, approved: str) -> str:
    """`url` itself when it is on the origin of `approved`; a pagination link anywhere else is refused, since the credential headers would follow it."""
    origin = Origin.parse(approved)

    if origin is None:
        raise DestinationError(f"not an http(s) URL: {approved!r}")

    try:
        return origin.require(url)
    except OriginError as e:
        raise DestinationError(str(e)) from e


class Redirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to an address the network policy admits, and drops every header but `accept` and `user-agent` once it leaves the origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)

        if new is None:
            return None

        network_policy().check(new.full_url)

        if Origin.parse(new.full_url) != Origin.parse(req.full_url):
            new.headers = {
                k: v for k, v in new.headers.items() if k.lower() in SAFE_HEADERS
            }
            new.unredirected_hdrs = {}

        return new


OPENER = urllib.request.build_opener(Redirects)


def urlopen(request: urllib.request.Request, timeout: Optional[float] = None) -> Any:
    """`urllib.request.urlopen` for a request that may carry credentials: the destination is checked first and every redirect after."""
    network_policy().check(request.full_url)

    return OPENER.open(request, timeout=timeout)
