from addon.bb8_core.ble_bridge import BLEBridge


class Gw:
    def resolve_adapter(self):
        return "hci0"


gw = Gw()
b = BLEBridge(gw, target_mac="00:11:22:33:44:55", ble_adapter="hci0")
for name in (
    "power",
    "stop",
    "set_led_off",
    "set_led_rgb",
    "sleep",
    "is_connected",
    "get_rssi",
):
    print(name, hasattr(b, name), getattr(b, name))
