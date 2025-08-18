from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass
import inspect


async def resolve_services(client: Any) -> Optional[Any]:
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
            return await get_svc()
        result = get_svc()
        if inspect.isawaitable(result):
            return await result  # some wrappers return awaitable callables
        return result

    # Fallback to property-style access
    if hasattr(client, "services"):
        return getattr(client, "services")

    return None
