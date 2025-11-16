#!/usr/bin/env python3
"""
BB-8 Sphero Protocol Wake Test

Uses proper Sphero BLE packet format based on reverse-engineered protocol.
"""

import asyncio
from datetime import datetime

from bleak import BleakClient

# BB-8 Primary Device
BB8_PRIMARY = {
    "name": "BB-B54A",
    "address": "259ED00E-3026-2568-C410-4590C9A9297C",
}

# Sphero BLE Protocol Constants
SPHERO_SERVICE_UUID = "22bb746f-2bb0-7554-2d6f-726568705327"
SPHERO_COMMAND_UUID = "22bb746f-2ba1-7554-2d6f-726568705327"  # TX (write to robot)
SPHERO_RESPONSE_UUID = "22bb746f-2ba6-7554-2d6f-726568705327"  # RX (read from robot)


def create_sphero_packet(device_id, command_id, seq_num, data=b""):
    """Create a proper Sphero API packet"""
    # Sphero packet format: [SOP1][SOP2][DID][CID][SEQ][DLEN][DATA...][CHK]
    sop1 = 0xFF  # Start of packet 1
    sop2 = 0xFF  # Start of packet 2 (response required)
    did = device_id  # Device ID
    cid = command_id  # Command ID
    seq = seq_num & 0xFF  # Sequence number
    dlen = len(data)  # Data length

    # Calculate checksum
    checksum = (did + cid + seq + dlen + sum(data)) & 0xFF
    checksum = (~checksum) & 0xFF

    packet = bytes([sop1, sop2, did, cid, seq, dlen]) + data + bytes([checksum])
    return packet


async def send_sphero_commands():
    """Send proper Sphero protocol commands"""
    print("🎯 Connecting to BB-8 with Sphero protocol...")

    try:
        async with BleakClient(BB8_PRIMARY["address"], timeout=15.0) as client:
            print("✅ Connected to BB-B54A")

            # Find the correct characteristic
            command_char = None
            for service in client.services:
                for char in service.characteristics:
                    if "write" in [prop.lower() for prop in char.properties]:
                        command_char = char.uuid
                        break
                if command_char:
                    break

            if not command_char:
                print("❌ No command characteristic found")
                return False

            print(f"🎯 Using characteristic: {command_char}")
            print("=" * 50)

            # Sequence 1: Wake command
            print("🚀 1. Sending Sphero Wake Command...")
            wake_packet = create_sphero_packet(
                0x00, 0x01, 0x01
            )  # Core device, Ping command
            print(f"   📦 Wake packet: {wake_packet.hex()}")
            await client.write_gatt_char(command_char, wake_packet, response=False)
            await asyncio.sleep(1.0)

            # Sequence 2: LED Control Commands
            print("💡 2. Sending LED Commands...")

            # Red LED
            led_red = create_sphero_packet(
                0x00, 0x20, 0x02, bytes([255, 0, 0, 0])
            )  # Set RGB LED
            print("   🔴 Red LED")
            await client.write_gatt_char(command_char, led_red, response=False)
            await asyncio.sleep(1.0)

            # Green LED
            led_green = create_sphero_packet(0x00, 0x20, 0x03, bytes([0, 255, 0, 0]))
            print("   🟢 Green LED")
            await client.write_gatt_char(command_char, led_green, response=False)
            await asyncio.sleep(1.0)

            # Blue LED
            led_blue = create_sphero_packet(0x00, 0x20, 0x04, bytes([0, 0, 255, 0]))
            print("   🔵 Blue LED")
            await client.write_gatt_char(command_char, led_blue, response=False)
            await asyncio.sleep(1.0)

            # White LED (bright)
            led_white = create_sphero_packet(
                0x00, 0x20, 0x05, bytes([255, 255, 255, 0])
            )
            print("   ⚪ White LED")
            await client.write_gatt_char(command_char, led_white, response=False)
            await asyncio.sleep(1.5)

            # LED Off
            led_off = create_sphero_packet(0x00, 0x20, 0x06, bytes([0, 0, 0, 0]))
            print("   ⚫ LED Off")
            await client.write_gatt_char(command_char, led_off, response=False)
            await asyncio.sleep(0.5)

            # Sequence 3: Movement Commands
            print("🤖 3. Sending Movement Commands...")

            # Roll command - small movement
            roll_cmd = create_sphero_packet(
                0x02, 0x30, 0x07, bytes([50, 0, 1])
            )  # Speed 50, heading 0, state 1
            print("   ➡️ Roll forward (slow)")
            await client.write_gatt_char(command_char, roll_cmd, response=False)
            await asyncio.sleep(2.0)

            # Stop command
            stop_cmd = create_sphero_packet(
                0x02, 0x30, 0x08, bytes([0, 0, 0])
            )  # Speed 0
            print("   ⏹️ Stop")
            await client.write_gatt_char(command_char, stop_cmd, response=False)
            await asyncio.sleep(1.0)

            # Sequence 4: Alternative wake attempts
            print("🔄 4. Alternative Wake Protocols...")

            # Simple wake bytes (common in Sphero protocols)
            simple_wakes = [
                b"\\x68\\x65\\x6C\\x6C\\x6F",  # "hello"
                b"\\xFF\\xFE\\x00\\x01\\x01\\x00\\xFD",  # Standard wake
                b"\\x8D\\x0A\\x00\\x01\\x00\\x76",  # Sphero wake packet
            ]

            for i, wake_bytes in enumerate(simple_wakes):
                print(f"   📤 Wake attempt {i + 1}: {wake_bytes.hex()}")
                await client.write_gatt_char(command_char, wake_bytes, response=False)
                await asyncio.sleep(0.8)

            # Final sequence - attention grabber
            print("🎆 5. Final Attention Sequence...")
            for _ in range(3):
                # Bright flash
                await client.write_gatt_char(command_char, led_white, response=False)
                await asyncio.sleep(0.3)
                await client.write_gatt_char(command_char, led_off, response=False)
                await asyncio.sleep(0.3)

            print("=" * 50)
            print("✅ All Sphero protocol commands sent!")
            return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


async def main():
    """Main test with Sphero protocol"""
    print("=" * 70)
    print("🤖 BB-8 Sphero Protocol Wake Test")
    print("=" * 70)
    print(f"📅 Test started: {datetime.now().isoformat()}")
    print("🏠 Environment: BB-8 REMOVED from charging cradle")
    print()
    print("👁️  ENHANCED VISUAL TEST:")
    print("   Watch BB-8 very carefully for:")
    print("   • ANY LED activity (even brief flashes)")
    print("   • ANY movement, rotation, or vibration")
    print("   • Head movements or body shifts")
    print("   • ANY sounds, beeps, or audio responses")
    print("   • Changes in BB-8's posture or position")
    print()

    input("🚀 Press ENTER to start Sphero protocol wake test...")

    success = await send_sphero_commands()

    print()
    print("🏁 SPHERO PROTOCOL TEST COMPLETE!")
    print("=" * 70)

    if success:
        print("✅ All Sphero protocol commands sent successfully")
        print()
        print("🔍 CRITICAL OBSERVATION QUESTIONS:")
        print("   Did you see ANY response at all?")
        print("   - Even a tiny LED flicker?")
        print("   - Any slight movement or vibration?")
        print("   - Any change in BB-8's state?")
        print()

        response = input("🤔 Any response observed this time? (y/n): ").lower().strip()

        if response.startswith("y"):
            print()
            print("🎉 BREAKTHROUGH! SPHERO PROTOCOL WORKING!")
            print("✅ Wake-up signal successfully replicated!")
            print("🎯 BB-B54A confirmed as command interface")
            print("📡 Proper Sphero BLE protocol is the key")

            details = input("\\n📝 What did you observe? (LED/movement/sound): ")
            print(f"\\n📋 Response details: {details}")

        else:
            print()
            print("🤔 Still no response observed...")
            print("💭 Possible next steps:")
            print("   1. BB-8 may need to be 'awakened' by physical interaction first")
            print("   2. May require authentication/pairing handshake")
            print("   3. Could need different service/characteristic")
            print("   4. Timing may be critical")

            # One more attempt - try a different characteristic
            different_char = (
                input("\\n🔄 Try a different BLE characteristic? (y/n): ")
                .lower()
                .strip()
            )
            if different_char.startswith("y"):
                print("💡 Next test should try all 11 characteristics systematically")
    else:
        print("❌ Connection failed - BLE communication issues")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
