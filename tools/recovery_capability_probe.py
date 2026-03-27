#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

probe_host_bluetooth_recovery_capability = importlib.import_module(
    "bb8_core.recovery_capability_probe"
).probe_host_bluetooth_recovery_capability


async def _main() -> None:
    result = await probe_host_bluetooth_recovery_capability(source="manual_tool")
    print(json.dumps(result, separators=(",", ":"), indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
