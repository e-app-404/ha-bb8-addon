#!/usr/bin/env python3
"""
BB-8 Wake-up Signal Replication Test (Spherov2 SDK)

Uses the spherov2 SDK to properly connect to BB-8 and test wake-up commands.
"""

import asyncio
import time
from datetime import datetime

from bleak import BleakScanner

try:
    from spherov2 import scanner
    from spherov2.adapter.tcp_adapter import TcpAdapter
    from spherov2.toy.bb8 import BB8

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


async def monitor_signal_strength(device_name, duration=8):
    """Monitor signal strength for a specific device"""
    print(f"📡 Monitoring {device_name} signal strength for {duration}s...")

    start_time = time.time()
    readings = []

    while time.time() - start_time < duration:
        try:
            devices = await BleakScanner.discover(timeout=2.0)
            for device in devices:
                if device.name == device_name:
                    rssi = getattr(device, "rssi", None)
                    if rssi:
                        timestamp = time.time() - start_time
                        readings.append((timestamp, rssi))
                        print(f"  {timestamp:.1f}s: {rssi} dBm")
                    break
        except:
            pass
        await asyncio.sleep(1.0)

    return readings


def connect_and_wake_bb8():
    """Connect to BB-8 using spherov2 and send wake commands"""
    print("🔄 Scanning for BB-8 with spherov2...")

    if not SDK_AVAILABLE:
        print("❌ Spherov2 SDK not available")
        return False

    try:
        # Scan for toys
        toys = scanner.find_toys()
        print(f"📋 Found {len(toys)} toys")

        bb8_toy = None
        for toy in toys:
            print(f"  🤖 Found: {toy.name} ({toy.address})")
            if "bb" in toy.name.lower():
                bb8_toy = toy
                break

        if not bb8_toy:
            print("❌ No BB-8 found")
            return False

        print(f"🎯 Connecting to {bb8_toy.name}...")

        # Connect
        with BB8(bb8_toy) as bb8:
            print("✅ Connected to BB-8!")

            # Send wake-up commands
            print("🚀 Sending wake-up commands...")

            # 1. Wake command
            bb8.wake()
            time.sleep(1)
            print("  ✅ Wake command sent")

            # 2. LED flash to simulate wake activity
            bb8.set_main_led(255, 255, 255)  # White flash
            time.sleep(0.5)
            bb8.set_main_led(0, 0, 0)  # Turn off
            time.sleep(0.5)
            bb8.set_main_led(0, 255, 0)  # Green flash
            time.sleep(0.5)
            bb8.set_main_led(0, 0, 0)  # Turn off
            print("  ✅ LED wake sequence complete")

            # 3. Small movement to simulate wake
            bb8.roll(0, 0, 1)  # Brief movement
            time.sleep(1)
            print("  ✅ Movement command sent")

            return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_spherov2_wake():
    """Main test using spherov2 SDK"""
    print("=" * 60)
    print("🤖 BB-8 Wake-up Signal Replication Test (Spherov2)")
    print("=" * 60)
    print(f"📅 Test started: {datetime.now().isoformat()}")
    print("🏠 Environment: BB-8 docked on charging cradle")
    print()

    # Phase 1: Baseline signal strength
    print("📊 PHASE 1: Baseline Signal Monitoring")
    baseline_bb54a = await monitor_signal_strength("BB-B54A", 6)
    baseline_s33 = await monitor_signal_strength("S33 BB84 LE", 6)

    print()
    print("🔧 PHASE 2: Spherov2 Wake-up Commands")

    # Run spherov2 commands in a separate thread
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(connect_and_wake_bb8)
        try:
            success = future.result(timeout=30)  # 30 second timeout
            if success:
                print("✅ Spherov2 wake commands completed successfully")
            else:
                print("❌ Spherov2 wake commands failed")
        except concurrent.futures.TimeoutError:
            print("⏰ Spherov2 wake commands timed out")

    print()
    print("📊 PHASE 3: Post-Wake Signal Monitoring")
    post_bb54a = await monitor_signal_strength("BB-B54A", 6)
    post_s33 = await monitor_signal_strength("S33 BB84 LE", 6)

    # Analyze results
    print()
    print("📈 ANALYSIS:")

    def analyze_signal_change(baseline, post, device_name):
        if baseline and post:
            baseline_avg = sum(reading[1] for reading in baseline) / len(baseline)
            post_avg = sum(reading[1] for reading in post) / len(post)
            change = post_avg - baseline_avg
            print(f"  {device_name}:")
            print(f"    Baseline: {baseline_avg:.1f} dBm (n={len(baseline)})")
            print(f"    Post-cmd: {post_avg:.1f} dBm (n={len(post)})")
            print(
                f"    Change: {change:+.1f} dBm {'📈 STRONGER' if change > 3 else '📉 WEAKER' if change < -3 else '➡️ STABLE'}"
            )
            return change
        else:
            print(f"  {device_name}: No data collected")
            return 0

    bb54a_change = analyze_signal_change(baseline_bb54a, post_bb54a, "BB-B54A")
    s33_change = analyze_signal_change(baseline_s33, post_s33, "S33 BB84 LE")

    print()
    print("🏁 CONCLUSION:")
    if abs(bb54a_change) > 4 or abs(s33_change) > 4:
        print("✅ WAKE-UP SIGNAL REPLICATED! Significant RSSI change detected.")
        print("🎉 Programmatic wake-up appears successful!")
        if bb54a_change > 4:
            print("📡 BB-B54A showed strongest response - primary wake interface")
        if s33_change > 4:
            print("📡 S33 BB84 LE showed strongest response - operational interface")
    elif abs(bb54a_change) > 2 or abs(s33_change) > 2:
        print("🤔 PARTIAL SUCCESS: Moderate RSSI change detected.")
        print("💡 Wake-up may have partially succeeded.")
    else:
        print("❓ INCONCLUSIVE: No significant RSSI change detected.")
        print("💡 Wake-up signal may not affect BLE advertising strength.")

    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_spherov2_wake())
