#!/usr/bin/env python3
"""
BB-8 Wake-up Signal Replication Test

Tests whether we can programmatically replicate the physical wake-up button press
by sending appropriate BLE commands to trigger the same response.
"""

import asyncio
import time
from datetime import datetime

from bleak import BleakClient, BleakScanner

# BB-8 device addresses from our analysis
BB8_DEVICES = {
    "BB-B54A": "259ED00E-3026-2568-C410-4590C9A9297C",
    "S33 BB84 LE": "09C6CEBB-2743-A94A-73FC-A7B36E5F5864",
}

# Known Sphero/BB-8 GATT characteristics
SPHERO_CHARACTERISTICS = {
    "command": "22bb746f-2bb0-7554-2d6f-726568705327",  # Command characteristic
    "response": "22bb746f-2ba6-7554-2d6f-726568705327",  # Response characteristic
    "wake": "22bb746f-2bbf-7554-2d6f-726568705327",  # Wake characteristic (if exists)
}


async def scan_for_signal_strength(device_name, duration=10):
    """Monitor signal strength for a specific device"""
    print(f"📡 Monitoring {device_name} signal strength for {duration}s...")

    start_time = time.time()
    readings = []

    while time.time() - start_time < duration:
        devices = await BleakScanner.discover(timeout=1.0)
        for device in devices:
            if device.name == device_name:
                rssi = getattr(device, "rssi", None)
                if rssi:
                    timestamp = time.time() - start_time
                    readings.append((timestamp, rssi))
                    print(f"  {timestamp:.1f}s: {rssi} dBm")
                break
        await asyncio.sleep(0.5)

    return readings


async def send_wake_command(device_address, device_name):
    """Attempt to send wake-up command to BB-8"""
    print(f"🔄 Attempting to connect to {device_name} ({device_address})...")

    try:
        async with BleakClient(device_address) as client:
            print(f"✅ Connected to {device_name}")

            # Get services
            services = client.services
            print(f"📋 Found {len(services)} services")

            # Look for command characteristics
            command_char = None
            for service in services:
                for char in service.characteristics:
                    print(f"  📝 Characteristic: {char.uuid} - {char.properties}")
                    if "write" in [prop.lower() for prop in char.properties]:
                        command_char = char.uuid
                        print(f"    🎯 Found writable characteristic: {char.uuid}")

            if command_char:
                print(f"🚀 Sending wake-up command to {command_char}...")

                # Try various wake-up commands
                wake_commands = [
                    b"\x01",  # Simple wake
                    b"\x00\x01",  # Wake with prefix
                    b"\x13",  # Wake command from spherov2
                    b"\x8d\x13\x00\x00\x00\xd5",  # Full Sphero wake packet
                ]

                for i, cmd in enumerate(wake_commands):
                    try:
                        print(f"  📤 Command {i + 1}: {cmd.hex()}")
                        await client.write_gatt_char(command_char, cmd, response=False)
                        await asyncio.sleep(1)
                        print(f"    ✅ Command {i + 1} sent successfully")
                    except Exception as e:
                        print(f"    ❌ Command {i + 1} failed: {e}")

                return True
            else:
                print("❌ No writable characteristics found")
                return False

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_wake_replication():
    """Main test function to replicate wake-up signal"""
    print("=" * 60)
    print("🤖 BB-8 Wake-up Signal Replication Test")
    print("=" * 60)
    print(f"📅 Test started: {datetime.now().isoformat()}")
    print("🏠 Environment: BB-8 docked on charging cradle")
    print()

    # Phase 1: Baseline signal strength
    print("📊 PHASE 1: Baseline Signal Monitoring")
    baseline_bb54a = await scan_for_signal_strength("BB-B54A", 5)
    baseline_s33 = await scan_for_signal_strength("S33 BB84 LE", 5)

    print()
    print("🔧 PHASE 2: Programmatic Wake-up Attempt")

    # Try both devices
    for device_name, device_address in BB8_DEVICES.items():
        print(f"\n🎯 Testing {device_name}...")
        success = await send_wake_command(device_address, device_name)
        if success:
            print(f"✅ Commands sent to {device_name}")
        else:
            print(f"❌ Failed to send commands to {device_name}")

        await asyncio.sleep(2)

    print()
    print("📊 PHASE 3: Post-Command Signal Monitoring")
    post_bb54a = await scan_for_signal_strength("BB-B54A", 5)
    post_s33 = await scan_for_signal_strength("S33 BB84 LE", 5)

    # Analyze results
    print()
    print("📈 ANALYSIS:")

    def analyze_signal_change(baseline, post, device_name):
        if baseline and post:
            baseline_avg = sum(reading[1] for reading in baseline) / len(baseline)
            post_avg = sum(reading[1] for reading in post) / len(post)
            change = post_avg - baseline_avg
            print(f"  {device_name}:")
            print(f"    Baseline: {baseline_avg:.1f} dBm")
            print(f"    Post-cmd: {post_avg:.1f} dBm")
            print(
                f"    Change: {change:+.1f} dBm {'📈' if change > 2 else '📉' if change < -2 else '➡️'}"
            )
            return change
        return 0

    bb54a_change = analyze_signal_change(baseline_bb54a, post_bb54a, "BB-B54A")
    s33_change = analyze_signal_change(baseline_s33, post_s33, "S33 BB84 LE")

    print()
    print("🏁 CONCLUSION:")
    if abs(bb54a_change) > 3 or abs(s33_change) > 3:
        print("✅ WAKE-UP SIGNAL REPLICATED! Significant RSSI change detected.")
        print("🎉 Programmatic wake-up appears successful!")
    else:
        print("❓ INCONCLUSIVE: No significant RSSI change detected.")
        print("💡 May need different command sequence or authentication.")

    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_wake_replication())
