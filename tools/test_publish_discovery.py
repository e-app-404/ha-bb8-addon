import asyncio
import os

from bb8_core.bb8_presence_scanner import publish_discovery

os.environ["MQTT_BASE"] = "bb8/testbb8"


class DummyMQTT:
    async def publish(self, topic, payload, qos, retain):
        print(f"publish: {topic}")
        return None


if __name__ == "__main__":
    asyncio.run(publish_discovery(DummyMQTT(), "testbb8"))
