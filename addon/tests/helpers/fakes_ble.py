class FakeBLEDevice:
    def __init__(
        self, addr, name, rssi, services=None, fail_connect=False, fail_read=False
    ):
        self.addr = addr
        self.name = name
        self.rssi = rssi
        self.services = services or []
        self.connected = False
        self.fail_connect = fail_connect
        self.fail_read = fail_read

    def connect(self):
        import logging

        if self.fail_connect:
            raise RuntimeError("connect failed")
        self.connected = True
        logging.getLogger("bb8.ble").info(f"connect: {self.addr}")

    def disconnect(self):
        self.connected = False

    def read_gatt(self, service):
        import logging

        if self.fail_read:
            raise RuntimeError("read_gatt failed")
        logging.getLogger("bb8.ble").info(f"read: {service}")
        return b"data-for-%s" % service.encode()


class FakeBLEAdapter:
    def __init__(self):
        self.scanning = False
        self.callbacks = []
        self.devices = []
        self.fail_scan = False

    def start_scan(self):
        if self.fail_scan:
            raise RuntimeError("scan failed")
        self.scanning = True

    def stop_scan(self):
        self.scanning = False

    def register_callback(self, cb):
        self.callbacks.append(cb)

    def emit_discovery(self, device):
        for cb in self.callbacks:
            cb(device)

    def add_device(self, device):
        self.devices.append(device)

    def inject_error(self, error_type):
        if error_type == "scan":
            self.fail_scan = True
