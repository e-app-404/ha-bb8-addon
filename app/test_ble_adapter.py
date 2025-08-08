import os

def check_ble_adapter():
    # Check for BLE device node
    hci_found = any(dev.startswith('hci') for dev in os.listdir('/sys/class/bluetooth/'))

    if hci_found:
        print("[BLE] hci adapter found. Adapter is ready.")
    else:
        print("[BLE] No adapter")

if __name__ == "__main__":
    check_ble_adapter()
