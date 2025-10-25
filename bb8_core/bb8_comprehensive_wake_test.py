#!/usr/bin/env python3
"""
BB-8 Wake-up Signal Replication Test (Direct BLE)

Direct BLE approach using known BB-8 command protocols.
"""

import asyncio
import time
from datetime import datetime

from bleak import BleakClient, BleakScanner

# BB-8 devices from our analysis
BB8_DEVICES = {
    "BB-B54A": "259ED00E-3026-2568-C410-4590C9A9297C",
    "S33 BB84 LE": "09C6CEBB-2743-A94A-73FC-A7B36E5F5864",
}


async def monitor_both_devices(duration=10):
    """Monitor both BB-8 devices simultaneously"""
    print(f"📡 Monitoring both devices for {duration}s...")

    start_time = time.time()
    readings = {"BB-B54A": [], "S33 BB84 LE": []}

    while time.time() - start_time < duration:
        try:
            devices = await BleakScanner.discover(timeout=1.5)
            timestamp = time.time() - start_time

            for device in devices:
                if device.name in readings:
                    rssi = getattr(device, "rssi", None)
                    if rssi:
                        readings[device.name].append((timestamp, rssi))
                        print(f"  {timestamp:.1f}s {device.name}: {rssi} dBm")
        except Exception as e:
            print(f"  Scan error: {e}")

        await asyncio.sleep(0.8)

    return readings


async def attempt_direct_wake_commands():
    """Try direct BLE wake commands on both interfaces"""
    print("🚀 Attempting direct wake commands...")

    wake_success = False

    for device_name, device_address in BB8_DEVICES.items():
        print(f"\n🎯 Testing {device_name}...")

        try:
            async with BleakClient(device_address, timeout=10.0) as client:
                print(f"✅ Connected to {device_name}")

                # Find writable characteristics
                write_chars = []
                for service in client.services:
                    for char in service.characteristics:
                        if "write" in [
                            prop.lower() for prop in char.properties
                        ]:
                            write_chars.append(char.uuid)

                print(f"📝 Found {len(write_chars)} writable characteristics")

                if write_chars:
                    # Try different wake command sequences
                    wake_commands = [
                        # Basic wake sequences
                        bytes([0x01]),
                        bytes([0x13]),  # Sphero wake command
                        bytes([0x00, 0x01]),
                        bytes([0xFF, 0x01]),
                        # LED commands (should cause visual response)
                        bytes([0x02, 0xFF, 0x00, 0x00]),  # Red LED
                        bytes([0x02, 0x00, 0xFF, 0x00]),  # Green LED
                        bytes([0x02, 0x00, 0x00, 0xFF]),  # Blue LED
                        bytes([0x02, 0x00, 0x00, 0x00]),  # LED off
                        # Movement commands (small test movements)
                        bytes([0x03, 0x10, 0x00]),  # Small forward
                        bytes([0x03, 0x00, 0x00]),  # Stop
                    ]

                    for i, cmd in enumerate(wake_commands):
                        for char_uuid in write_chars[
                            :2
                        ]:  # Try first 2 characteristics
                            try:
                                print(
                                    f"  📤 Cmd {i + 1} to {char_uuid[:8]}...: {cmd.hex()}"
                                )
                                await client.write_gatt_char(
                                    char_uuid, cmd, response=False
                                )
                                await asyncio.sleep(0.3)
                                wake_success = True
                                print("    ✅ Command sent successfully")
                            except Exception as e:
                                print(
                                    f"    ⚠️  Command failed: {str(e)[:50]}..."
                                )

                    # Brief pause between devices
                    await asyncio.sleep(1)
                else:
                    print("❌ No writable characteristics found")

        except Exception as e:
            print(f"❌ Connection to {device_name} failed: {e}")

    return wake_success


async def test_wake_replication_comprehensive():
    """Comprehensive wake-up replication test"""
    print("=" * 70)
    print("🤖 BB-8 Wake-up Signal Replication Test (Comprehensive)")
    print("=" * 70)
    print(f"📅 Test started: {datetime.now().isoformat()}")
    print("🏠 Environment: BB-8 docked on charging cradle")
    print()

    # Phase 1: Extended baseline monitoring
    print("📊 PHASE 1: Extended Baseline Monitoring")
    baseline = await monitor_both_devices(8)

    print()
    print("🔧 PHASE 2: Direct BLE Wake Commands")
    commands_sent = await attempt_direct_wake_commands()

    if commands_sent:
        print("✅ Wake commands sent successfully")
        # Wait a moment for effects
        await asyncio.sleep(2)
    else:
        print("❌ No wake commands could be sent")

    print()
    print("📊 PHASE 3: Post-Command Extended Monitoring")
    post_cmd = await monitor_both_devices(8)

    # Phase 4: Analysis
    print()
    print("📈 DETAILED ANALYSIS:")

    def detailed_analysis(baseline_data, post_data, device_name):
        print(f"\n  📱 {device_name}:")

        if baseline_data and post_data:
            # Calculate statistics
            baseline_values = [r[1] for r in baseline_data]
            post_values = [r[1] for r in post_data]

            baseline_avg = sum(baseline_values) / len(baseline_values)
            post_avg = sum(post_values) / len(post_values)
            change = post_avg - baseline_avg

            baseline_min, baseline_max = (
                min(baseline_values),
                max(baseline_values),
            )
            post_min, post_max = min(post_values), max(post_values)

            print(
                f"    Baseline: {baseline_avg:.1f} dBm (range: {baseline_min} to {baseline_max}, n={len(baseline_values)})"
            )
            print(
                f"    Post-cmd: {post_avg:.1f} dBm (range: {post_min} to {post_max}, n={len(post_values)})"
            )
            print(f"    Change: {change:+.1f} dBm", end="")

            if abs(change) >= 5:
                print(" 🔥 MAJOR CHANGE!")
                return "major"
            elif abs(change) >= 3:
                print(" 📈 SIGNIFICANT CHANGE")
                return "significant"
            elif abs(change) >= 1.5:
                print(" 📊 MINOR CHANGE")
                return "minor"
            else:
                print(" ➡️ STABLE")
                return "stable"
        else:
            print(
                f"    ❌ Insufficient data (baseline: {len(baseline_data) if baseline_data else 0}, post: {len(post_data) if post_data else 0})"
            )
            return "no_data"

    bb54a_result = detailed_analysis(
        baseline.get("BB-B54A", []), post_cmd.get("BB-B54A", []), "BB-B54A"
    )
    s33_result = detailed_analysis(
        baseline.get("S33 BB84 LE", []),
        post_cmd.get("S33 BB84 LE", []),
        "S33 BB84 LE",
    )

    print()
    print("🏁 FINAL CONCLUSION:")

    if bb54a_result == "major" or s33_result == "major":
        print("🎉 SUCCESS! WAKE-UP SIGNAL SUCCESSFULLY REPLICATED!")
        print("📡 Major RSSI changes detected - programmatic wake-up works!")
        if bb54a_result == "major":
            print("🎯 BB-B54A is the primary wake-responsive interface")
        if s33_result == "major":
            print("🎯 S33 BB84 LE is the primary wake-responsive interface")

    elif bb54a_result == "significant" or s33_result == "significant":
        print("✅ LIKELY SUCCESS! Significant signal changes detected.")
        print("💡 Wake-up commands appear to have activated BB-8.")

    elif bb54a_result == "minor" or s33_result == "minor":
        print("🤔 POSSIBLE SUCCESS: Minor changes detected.")
        print("💭 Wake-up may have partially succeeded.")

    else:
        print("❓ INCONCLUSIVE: No significant changes detected.")
        print(
            "💡 Either wake-up failed, or wake-up doesn't affect BLE advertising."
        )
        print("🔧 Recommendation: Try physical wake-up button for comparison.")

    print()
    if commands_sent:
        print("📋 Commands were successfully sent via BLE")
    else:
        print("⚠️  No BLE commands could be sent - connection issues")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_wake_replication_comprehensive())
