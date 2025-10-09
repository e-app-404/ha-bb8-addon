#!/usr/bin/env python3
"""
BB-8 All Characteristics Wake Test

Systematically tests all 11 writable characteristics to find the correct command channel.
"""

import asyncio
from datetime import datetime

from bleak import BleakClient

# BB-8 Primary Device
BB8_PRIMARY = {
    "name": "BB-B54A",
    "address": "259ED00E-3026-2568-C410-4590C9A9297C",
}


async def test_all_characteristics():
    """Test wake commands on all available characteristics"""
    print("🎯 Connecting to BB-8 for comprehensive characteristic test...")

    try:
        async with BleakClient(BB8_PRIMARY["address"], timeout=15.0) as client:
            print("✅ Connected to BB-B54A")

            # Collect all writable characteristics
            write_chars = []
            for service in client.services:
                print(f"\\n📋 Service: {service.uuid}")
                for char in service.characteristics:
                    props = [prop.lower() for prop in char.properties]
                    if "write" in props:
                        write_chars.append({
                            "uuid": char.uuid,
                            "service": service.uuid,
                            "properties": char.properties,
                        })
                        print(
                            f"  ✍️  Writable: {char.uuid} | Props: {char.properties}"
                        )
                    else:
                        print(
                            f"  📖 Read-only: {char.uuid} | Props: {char.properties}"
                        )

            print(
                f"\\n🎯 Found {len(write_chars)} writable characteristics to test"
            )
            print("=" * 60)

            # Test commands for each characteristic
            test_commands = [
                (b"\\x01", "Basic wake (0x01)"),
                (b"\\x13", "Sphero wake (0x13)"),
                (b"\\xFF\\xFE\\x00\\x01\\x01\\x00\\xFD", "Sphero packet wake"),
                (b"\\x02\\xFF\\x00\\x00", "LED Red command"),
                (b"\\x02\\x00\\xFF\\x00", "LED Green command"),
                (b"\\x02\\x00\\x00\\x00", "LED Off command"),
            ]

            for i, char_info in enumerate(write_chars):
                char_uuid = char_info["uuid"]
                print(
                    f"\\n🧪 TESTING CHARACTERISTIC {i + 1}/{len(write_chars)}"
                )
                print(f"   UUID: {char_uuid}")
                print(f"   Properties: {char_info['properties']}")
                print(f"   Service: {char_info['service']}")
                print("   " + "=" * 50)

                # Test each command on this characteristic
                for cmd_bytes, cmd_desc in test_commands:
                    try:
                        print(f"   📤 {cmd_desc}: {cmd_bytes.hex()}")
                        await client.write_gatt_char(
                            char_uuid, cmd_bytes, response=False
                        )
                        await asyncio.sleep(0.5)  # Brief pause between commands
                        print("      ✅ Sent successfully")
                    except Exception as e:
                        print(f"      ❌ Failed: {str(e)[:40]}...")

                # Pause between characteristics for observation
                print(
                    "\\n   ⏸️  Pausing 2 seconds - watch for any BB-8 response..."
                )
                await asyncio.sleep(2.0)

                # Ask for feedback after each characteristic
                if i < len(write_chars) - 1:  # Don't ask after the last one
                    user_input = (
                        input(
                            f"\\n   🤔 Any response from characteristic {i + 1}? (y/n/q to quit): "
                        )
                        .lower()
                        .strip()
                    )
                    if user_input.startswith("y"):
                        print(
                            f"\\n   🎉 SUCCESS! Characteristic {i + 1} is responsive!"
                        )
                        print(f"   🎯 Working UUID: {char_uuid}")
                        print(f"   📋 Service: {char_info['service']}")

                        # Do a more extensive test on this working characteristic
                        print(
                            "\\n   🚀 Running extended test on working characteristic..."
                        )

                        extended_commands = [
                            (b"\\x02\\xFF\\xFF\\xFF", "Bright white LED"),
                            (b"\\x02\\xFF\\x00\\x00", "Red LED"),
                            (b"\\x02\\x00\\xFF\\x00", "Green LED"),
                            (b"\\x02\\x00\\x00\\xFF", "Blue LED"),
                            (b"\\x02\\x00\\x00\\x00", "LED off"),
                            (b"\\x03\\x20\\x00", "Movement test"),
                            (b"\\x03\\x00\\x00", "Stop movement"),
                        ]

                        for ext_cmd, ext_desc in extended_commands:
                            print(f"      🎭 {ext_desc}")
                            await client.write_gatt_char(
                                char_uuid, ext_cmd, response=False
                            )
                            await asyncio.sleep(1.0)

                        return char_uuid  # Return the working characteristic

                    elif user_input.startswith("q"):
                        print("\\n   🛑 Test stopped by user")
                        break

            print("\\n" + "=" * 60)
            print("🏁 All characteristics tested")
            return None

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None


async def main():
    """Main comprehensive test"""
    print("=" * 70)
    print("🤖 BB-8 All Characteristics Wake Test")
    print("=" * 70)
    print(f"📅 Test started: {datetime.now().isoformat()}")
    print("🏠 Environment: BB-8 REMOVED from charging cradle")
    print()
    print("🔬 SYSTEMATIC APPROACH:")
    print("   Testing all 11 characteristics one by one")
    print("   Each characteristic gets 6 different commands")
    print("   Watch carefully after each characteristic!")
    print()
    print("👁️  WATCH FOR:")
    print("   • LED flashes or color changes")
    print("   • Any movement or vibration")
    print("   • Sounds or beeps")
    print("   • ANY change in BB-8's behavior")
    print()

    input("🚀 Press ENTER to start systematic characteristic testing...")

    working_char = await test_all_characteristics()

    print("\\n" + "=" * 70)
    print("🏁 COMPREHENSIVE TEST COMPLETE!")
    print("=" * 70)

    if working_char:
        print(f"🎉 SUCCESS! Found working characteristic: {working_char}")
        print("✅ Wake-up signal replication is POSSIBLE!")
        print("🎯 We can programmatically replicate the wake-up button!")

        # Save the result
        with open(
            "/Users/evertappels/actions-runner/Projects/HA-BB8/reports/bb8_working_characteristic.txt",
            "w",
        ) as f:
            f.write("BB-8 Working BLE Characteristic\\n")
            f.write(f"Found: {datetime.now().isoformat()}\\n")
            f.write(f"Device: BB-B54A ({BB8_PRIMARY['address']})\\n")
            f.write(f"Working UUID: {working_char}\\n")
            f.write("Status: Commands successfully executed\\n")

        print("📝 Results saved to reports/bb8_working_characteristic.txt")

    else:
        print("❓ No responsive characteristic found in this test")
        print("💭 Possible reasons:")
        print("   • BB-8 may be in deep sleep mode")
        print("   • May require authentication/handshake first")
        print("   • Commands may need different timing")
        print("   • Physical wake-up may be required first")
        print()
        print("🔄 Next steps:")
        print("   1. Try tapping BB-8 physically first, then retest")
        print("   2. Research Sphero authentication protocols")
        print("   3. Try with spherov2 SDK properly installed")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
