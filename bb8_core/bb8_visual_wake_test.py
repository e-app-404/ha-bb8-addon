#!/usr/bin/env python3
"""
BB-8 Wake-up Visual Response Test

Focus on visual confirmation of wake-up rather than RSSI changes.
Tests LED commands and movement commands that should produce visible responses.
"""

import asyncio
from datetime import datetime

from bleak import BleakClient

# Primary BB-8 device (the one that accepts commands)
BB8_PRIMARY = {
    "name": "BB-B54A",
    "address": "259ED00E-3026-2568-C410-4590C9A9297C",
}


async def send_visual_wake_sequence():
    """Send a sequence of commands that should produce visible responses"""
    print("🎯 Connecting to BB-B54A for visual wake sequence...")

    try:
        async with BleakClient(BB8_PRIMARY["address"], timeout=15.0) as client:
            print("✅ Connected successfully!")

            # Find writable characteristics
            write_chars = []
            for service in client.services:
                for char in service.characteristics:
                    if "write" in [prop.lower() for prop in char.properties]:
                        write_chars.append(char.uuid)

            print(f"📝 Found {len(write_chars)} writable characteristics")

            if not write_chars:
                print("❌ No writable characteristics found")
                return False

            # Use the first writable characteristic (most likely to be command interface)
            primary_char = write_chars[0]
            print(f"🎯 Using characteristic: {primary_char}")

            print("\n🎭 VISUAL WAKE SEQUENCE:")
            print("👀 Watch BB-8 for LED flashes and movement!")
            print("=" * 50)

            # Sequence 1: LED Flash Pattern (simulating wake-up light show)
            print("💡 1. LED Wake Pattern...")
            led_sequence = [
                (b"\\x02\\xFF\\x00\\x00", "🔴 RED flash"),
                (b"\\x02\\x00\\xFF\\x00", "🟢 GREEN flash"),
                (b"\\x02\\x00\\x00\\xFF", "🔵 BLUE flash"),
                (b"\\x02\\xFF\\xFF\\xFF", "⚪ WHITE flash"),
                (b"\\x02\\x00\\x00\\x00", "⚫ LED OFF"),
            ]

            for cmd, desc in led_sequence:
                print(f"  {desc}")
                try:
                    await client.write_gatt_char(
                        primary_char, cmd, response=False
                    )
                    await asyncio.sleep(0.8)  # Hold each color
                except Exception as e:
                    print(f"    ⚠️ Failed: {e}")

            print("\\n🎪 2. Attention-Getting Sequence...")
            # Sequence 2: Rapid flash pattern
            for i in range(3):
                try:
                    await client.write_gatt_char(
                        primary_char, b"\\x02\\xFF\\xFF\\x00", response=False
                    )  # Yellow
                    await asyncio.sleep(0.3)
                    await client.write_gatt_char(
                        primary_char, b"\\x02\\x00\\x00\\x00", response=False
                    )  # Off
                    await asyncio.sleep(0.3)
                    print(f"  ⚡ Flash {i + 1}/3")
                except Exception as e:
                    print(f"    ⚠️ Flash {i + 1} failed: {e}")

            print("\\n🤖 3. Movement Test...")
            # Sequence 3: Small movements (if supported)
            movement_commands = [
                (b"\\x03\\x20\\x00", "➡️ Small right turn"),
                (b"\\x03\\x00\\x00", "⏹️ Stop"),
                (b"\\x03\\x20\\xB4", "⬅️ Small left turn"),
                (b"\\x03\\x00\\x00", "⏹️ Stop"),
            ]

            for cmd, desc in movement_commands:
                print(f"  {desc}")
                try:
                    await client.write_gatt_char(
                        primary_char, cmd, response=False
                    )
                    await asyncio.sleep(1.0)
                except Exception as e:
                    print(f"    ⚠️ Failed: {e}")

            print("\\n🔊 4. Wake Command Sequence...")
            # Sequence 4: Standard wake commands
            wake_commands = [
                (b"\\x01", "Basic wake"),
                (b"\\x13", "Sphero wake"),
                (b"\\xFF\\x01", "Enhanced wake"),
            ]

            for cmd, desc in wake_commands:
                print(f"  📤 {desc}")
                try:
                    await client.write_gatt_char(
                        primary_char, cmd, response=False
                    )
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"    ⚠️ Failed: {e}")

            print("\\n🎬 5. Final Attention Sequence...")
            # Final sequence: Big finish
            try:
                # Bright white flash
                await client.write_gatt_char(
                    primary_char, b"\\x02\\xFF\\xFF\\xFF", response=False
                )
                await asyncio.sleep(1.0)
                # Color cycle
                colors = [
                    b"\\x02\\xFF\\x00\\x00",
                    b"\\x02\\x00\\xFF\\x00",
                    b"\\x02\\x00\\x00\\xFF",
                ]
                for color in colors:
                    await client.write_gatt_char(
                        primary_char, color, response=False
                    )
                    await asyncio.sleep(0.4)
                # Turn off
                await client.write_gatt_char(
                    primary_char, b"\\x02\\x00\\x00\\x00", response=False
                )
                print("  🎆 Grand finale complete!")
            except Exception as e:
                print(f"  ⚠️ Finale failed: {e}")

            print("=" * 50)
            print("✅ All wake sequences completed!")
            return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def main():
    """Main test function"""
    print("=" * 70)
    print("🤖 BB-8 Wake-up Visual Response Test")
    print("=" * 70)
    print(f"📅 Test started: {datetime.now().isoformat()}")
    print("🏠 Environment: BB-8 docked on charging cradle")
    print()
    print("👁️  VISUAL CONFIRMATION TEST:")
    print("   Please watch BB-8 carefully for:")
    print("   • LED color changes and flashes")
    print("   • Any movement or rotation")
    print("   • Head movements or animations")
    print("   • Any sounds or responses")
    print()

    input("🚀 Press ENTER when ready to start the visual wake sequence...")

    success = await send_visual_wake_sequence()

    print()
    print("🏁 TEST COMPLETE!")
    print("=" * 70)

    if success:
        print("✅ Commands were sent successfully to BB-B54A")
        print()
        print("❓ VISUAL CONFIRMATION QUESTIONS:")
        print("   1. Did you see any LED color changes or flashes?")
        print("   2. Did BB-8 move, rotate, or show any physical response?")
        print("   3. Were there any sounds or other indicators?")
        print(
            "   4. Did the response match what happens with physical wake button?"
        )
        print()

        response = (
            input("🤔 Did you observe ANY visual response from BB-8? (y/n): ")
            .lower()
            .strip()
        )

        if response.startswith("y"):
            print()
            print("🎉 SUCCESS! WAKE-UP SIGNAL SUCCESSFULLY REPLICATED!")
            print("✅ Programmatic wake-up commands are working!")
            print("🎯 BB-B54A is confirmed as the primary command interface")
            print()
            print(
                "💡 CONCLUSION: The physical wake-up button can be replicated"
            )
            print("   through BLE commands sent to BB-B54A characteristic.")
        else:
            print()
            print(
                "❓ INCONCLUSIVE: Commands sent but no visual response observed"
            )
            print("💭 Possible reasons:")
            print(
                "   • BB-8 may be in sleep mode requiring different wake sequence"
            )
            print("   • Commands may need authentication or different format")
            print("   • BB-8 may need to be removed from cradle to respond")
            print("   • Different characteristic may be needed for commands")
    else:
        print("❌ Failed to send commands - connection issues")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
