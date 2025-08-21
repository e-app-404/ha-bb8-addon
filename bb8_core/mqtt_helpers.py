from __future__ import annotations

import json
from typing import Any


async def publish_retain(
    mqtt: Any, topic: str, payload: Any, qos: int = 0, retain: bool = True
) -> None:
    """
    Publish with retain=True across differing client signatures.
    Tries (topic, payload, qos, retain) then kwargs fallback.
    Payload may be str/bytes or JSON-serializable object.
    """
    data = (
        payload
        if isinstance(payload, str | bytes)
        else json.dumps(payload, separators=(",", ":"))
    )
    # Common signature: (topic, payload, qos, retain)
    try:
        await mqtt.publish(topic, data, qos, retain)  # type: ignore[misc]
        return
    except TypeError:
        pass
    # Kwargs signature: (topic, payload, retain=..., qos=...)
    try:
        await mqtt.publish(topic, data, retain=retain, qos=qos)  # type: ignore[misc]
        return
    except TypeError:
        pass
    # Last resort: synchronous publish (returns immediately)
    res = mqtt.publish(topic, data, qos, retain)  # type: ignore[call-arg]
    return None
