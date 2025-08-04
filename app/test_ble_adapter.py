import subprocess

def check_ble_adapter():
    try:
        output = subprocess.check_output(["hciconfig"], text=True)
        if "hci0" in output:
            print("[BLE] hci0 found. Adapter is ready.")
        else:
            print("[BLE] No BLE adapter found.")
    except Exception as e:
        print(f"[BLE] Error accessing adapter: {e}")

if __name__ == "__main__":
    check_ble_adapter()
