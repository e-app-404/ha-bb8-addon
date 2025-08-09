import json

def discovery_payloads(device_id: str, name: str, manufacturer="Sphero", model="BB-8", sw_version="n/a"):
    base = f"bb8/{device_id}"
    dev = {
        "identifiers": [f"bb8_{device_id}"],
        "manufacturer": manufacturer,
        "model": model,
        "name": name,
        "sw_version": sw_version,
    }

    light = {
        "name": f"{name} LED",
        "uniq_id": f"{device_id}_led",
        "schema": "json",
        "cmd_t": f"{base}/cmd/led/set",
        "stat_t": f"{base}/state/led",
        "sup_clrm": ["rgb"],               # supported_color_modes
        "dev": dev,
    }

    sleep_btn = {
        "name": f"{name} Sleep",
        "uniq_id": f"{device_id}_sleep",
        "cmd_t": f"{base}/cmd/sleep",
        "payload_press": json.dumps({"after_ms": 0}),
        "dev": dev,
    }

    heading_num = {
        "name": f"{name} Heading",
        "uniq_id": f"{device_id}_heading",
        "cmd_t": f"{base}/cfg/heading/set",
        "stat_t": f"{base}/cfg/heading",
        "min": 0, "max": 359, "step": 1, "mode": "slider",
        "unit_of_meas": "°",
        "dev": dev,
    }

    speed_num = {
        "name": f"{name} Speed",
        "uniq_id": f"{device_id}_speed",
        "cmd_t": f"{base}/cfg/speed/set",
        "stat_t": f"{base}/cfg/speed",
        "min": 0, "max": 255, "step": 5, "mode": "slider",
        "unit_of_meas": "",
        "dev": dev,
    }

    drive_btn = {
        "name": f"{name} Drive",
        "uniq_id": f"{device_id}_drive",
        "cmd_t": f"{base}/cmd/drive",
        "payload_press": json.dumps({"heading_deg": "{{heading}}", "speed": "{{speed}}", "duration_ms": 1000}),
        "dev": dev,
    }

    # Map to HA discovery topics
    return [
        ("homeassistant/light/bb8_%s_led/config" % device_id, json.dumps(light)),
        ("homeassistant/button/bb8_%s_sleep/config" % device_id, json.dumps(sleep_btn)),
        ("homeassistant/number/bb8_%s_heading/config" % device_id, json.dumps(heading_num)),
        ("homeassistant/number/bb8_%s_speed/config" % device_id, json.dumps(speed_num)),
        ("homeassistant/button/bb8_%s_drive/config" % device_id, json.dumps(drive_btn)),
    ]
