#!/usr/bin/env python3
"""
BB-8 Wake-Up Signal Replication Tool

This tool attempts to replicate the wake-up signal that occurs when the physical
wake-up button is pressed on the BB-8 charging cradle.

Based on our analysis:
- BB-B54A interface shows strongest response to wake-up button
- S33 BB84 LE interface accepts writes without authentication
- Wake-up button causes 9+ dBm signal strength improvement

Usage:
    python3 bb8_wake_replication.py
    python3 bb8_wake_replication.py --monitor-only
    python3 bb8_wake_replication.py --interface bb8-b54a
"""

import argparse
import asyncio
import time

from bleak import BleakClient, BleakScanner


class BB8WakeReplicator:
    """Replicate BB-8 wake-up signals through BLE commands"""

    # Known BB-8 interfaces from analysis
    INTERFACES = {
        "bb8-b54a": {
            "address": "259ED00E-3026-2568-C410-4590C9A9297C",
            "name": "BB-B54A",
            "write_chars": [
                "22bb746f-2ba1-7554-2d6f-726568705327",  # Requires auth
                "22bb746f-2bb1-7554-2d6f-726568705327",  # Requires auth
            ],
            "requires_auth": True,
        },
        "s33-bb84": {
            "address": "09C6CEBB-2743-A94A-73FC-A7B36E5F5864",
            "name": "S33 BB84 LE",
            "write_chars": [
                "c44f42b1-f5cf-479b-b515-9f1bb0099c98",  # write-without-response
            ],
            "requires_auth": False,
        },
    }

    # Wake command patterns observed/inferred
    WAKE_COMMANDS = [
        (b"\x8d\x0a\x13\x0d\x00", "Standard Sphero wake command"),
        (b"\x8d\x0a\x13\x0d", "Wake command variant"),
        (b"\x01", "Simple wake byte"),
        (b"\x00\x01", "Wake with null prefix"),
        (b"\xff\x00\x01\x00", "Power-on sequence"),
        (b"WAKE", "Text wake command"),
        # Pattern observed from button press timing
        (b"\x01\x00\x8d\x0a\x13\x0d\x00\x01", "Button press simulation"),
    ]

    def __init__(self, interface="s33-bb84"):
        self.interface = self.INTERFACES[interface]
        self.address = self.interface["address"]

    async def monitor_rssi_changes(self, duration=10):
        """Monitor RSSI changes for both BB-8 interfaces"""
        print(f"📊 Monitoring RSSI changes for {duration} seconds...")

        start_time = time.time()
        readings = []

        while time.time() - start_time < duration:
            timestamp = time.time()
            devices = await BleakScanner.discover(timeout=2.0)

            current_reading = {"timestamp": timestamp}

            for d in devices:
                for iface_key, iface_data in self.INTERFACES.items():
                    if d.address == iface_data["address"]:
                        rssi = getattr(d, "rssi", None)
                        current_reading[iface_data["name"]] = rssi

            readings.append(current_reading)
            print(f"  {current_reading}")
            await asyncio.sleep(1)

        return readings

    async def send_wake_commands(self):
        """Send wake commands to BB-8 interface"""
        print(f"🤖 Sending wake commands to {self.interface['name']}")

        if self.interface["requires_auth"]:
            print("⚠️  Interface requires authentication - commands may fail")

        try:
            async with BleakClient(self.address, timeout=30.0) as client:
                print(f"✅ Connected to {self.interface['name']}")

                for write_char in self.interface["write_chars"]:
                    print(f"\n📡 Using characteristic: {write_char}")

                    for payload, description in self.WAKE_COMMANDS:
                        try:
                            print(
                                f"  🧪 {description}: {payload.hex() if len(payload) <= 8 else payload[:8].hex() + '...'}"
                            )

                            await client.write_gatt_char(
                                write_char,
                                payload,
                                response=not self.interface["requires_auth"],
                            )

                            print("     ✅ Command sent successfully")
                            await asyncio.sleep(
                                2
                            )  # Wait for potential response

                        except Exception as e:
                            error_msg = str(e)
                            if "insufficient" in error_msg.lower():
                                print(
                                    "     🔐 Authentication/authorization required"
                                )
                            else:
                                print(f"     ❌ Failed: {e}")

                        await asyncio.sleep(1)  # Brief pause between commands

                print(
                    "\n⏱️  Waiting 10 seconds to observe any BB-8 responses..."
                )
                await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ Connection failed: {e}")

    async def simulate_button_press_pattern(self):
        """Simulate the timing pattern of a physical button press"""
        print("🔥 SIMULATING PHYSICAL BUTTON PRESS PATTERN")

        if self.interface["requires_auth"]:
            print("⚠️  Cannot simulate on authenticated interface")
            return

        try:
            async with BleakClient(self.address, timeout=30.0) as client:
                print(f"✅ Connected to {self.interface['name']}")

                write_char = self.interface["write_chars"][0]

                # Simulate button press: quick sequence with timing
                button_sequence = [
                    (b"\x01", 0.1),  # Press
                    (b"\x8d\x0a\x13\x0d", 0.5),  # Wake command
                    (b"\x01", 0.1),  # Release
                ]

                print("📋 Button press sequence:")
                for i, (cmd, delay) in enumerate(button_sequence):
                    print(f"  {i + 1}. Send {cmd.hex()}")
                    await client.write_gatt_char(
                        write_char, cmd, response=False
                    )
                    await asyncio.sleep(delay)

                print("✅ Button press simulation complete")
                await asyncio.sleep(5)  # Observe response

        except Exception as e:
            print(f"❌ Button simulation failed: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="BB-8 Wake-Up Signal Replication"
    )
    parser.add_argument(
        "--interface",
        choices=["bb8-b54a", "s33-bb84"],
        default="s33-bb84",
        help="BB-8 interface to target",
    )
    parser.add_argument(
        "--monitor-only",
        action="store_true",
        help="Only monitor RSSI changes, don't send commands",
    )
    parser.add_argument(
        "--button-simulation",
        action="store_true",
        help="Simulate physical button press pattern",
    )

    args = parser.parse_args()

    replicator = BB8WakeReplicator(args.interface)

    print("🤖 BB-8 WAKE-UP SIGNAL REPLICATION TOOL")
    print("======================================")
    print(f"Target Interface: {replicator.interface['name']}")
    print(f"Target Address: {replicator.address}")

    if args.monitor_only:
        print("\n📊 RSSI MONITORING MODE")
        await replicator.monitor_rssi_changes(30)
    elif args.button_simulation:
        print("\n🔥 BUTTON PRESS SIMULATION MODE")
        await replicator.simulate_button_press_pattern()
    else:
        print("\n🧪 WAKE COMMAND TESTING MODE")
        await replicator.send_wake_commands()

    print("\n🏁 Test complete!")
    print("💡 Observe BB-8 for:")
    print("   - LED color changes")
    print("   - Movement or rolling")
    print("   - Sound effects")
    print("   - BLE signal strength changes")


if __name__ == "__main__":
    asyncio.run(main())
