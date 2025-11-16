from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass
import inspect
import re

_MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}(?:[:-]|$)){6}")


def is_valid_mac(mac: str) -> bool:
    """Return True if the provided string looks like a MAC address.

    This is a permissive check used by tests — it accepts common separators
    (colon or hyphen) and hex octets.
    """
    if not isinstance(mac, str):
        return False
    return bool(_MAC_RE.match(mac))


async def resolve_services(client: Any) -> Any | None:
    """
    Works with Bleak versions where:
      - await client.get_services() exists, OR
      - client.get_services() returns a non-awaitable collection, OR
      - services are exposed as client.services
    """
    # Prefer explicit API if present
    get_svc = getattr(client, "get_services", None)
    if get_svc:
        if inspect.iscoroutinefunction(get_svc):
            return await get_svc()  # pragma: no cover
        result = get_svc()  # pragma: no cover
        if inspect.isawaitable(result):
            return await result  # pragma: no cover
        return result  # pragma: no cover

    # Fallback to property-style access
    if hasattr(client, "services"):
        return client.services  # pragma: no cover

    return None
