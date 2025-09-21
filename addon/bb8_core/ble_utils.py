import inspect
from typing import Any


async def resolve_services(client: Any) -> Any | None:
    """Works with Bleak versions where:
    - await client.get_services() exists, OR
    - client.get_services() returns a non-awaitable collection, OR
    - services are exposed as client.services
    """
    # Prefer explicit API if present
    get_svc = getattr(client, "get_services", None)
    if get_svc:
        if inspect.iscoroutinefunction(get_svc):
            return await get_svc()
        result = get_svc()
        if inspect.isawaitable(result):
            return await result  # some wrappers return awaitable callables
        return result

    # Fallback to property-style access
    if hasattr(client, "services"):
        return client.services

    return None
