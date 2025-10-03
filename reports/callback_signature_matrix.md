# MQTT Callback Signature Compliance Checklist

| File                        | Callback Name      | Required Signature (VERSION2)                          | Status      | Notes |
|-----------------------------|--------------------|--------------------------------------------------------|-------------|-------|
| echo_responder.py           | on_connect         | (client, userdata, flags, rc, properties=None)         | [x]         |       |
| echo_responder.py           | on_message         | (client, userdata, msg)                                | [x]         |       |
| mqtt_dispatcher.py          | on_connect         | (client, userdata, flags, rc, properties=None)         | [x]         |       |
| mqtt_dispatcher.py          | on_message         | (client, userdata, msg)                                | [x]         |       |
| force_discovery_emit.py     | on_connect         | (client, userdata, flags, rc, properties=None)         | [x]         |       |
| force_discovery_emit.py     | on_message         | (client, userdata, msg)                                | [x]         |       |
| check_bridge_broker.py      | on_connect         | (client, userdata, flags, rc, properties=None)         | [x]         |       |
| check_bridge_broker.py      | on_message         | (client, userdata, msg)                                | [x]         |       |
| discovery_migrate.py        | on_connect         | (client, userdata, flags, rc, properties=None)         | [x]         |       |
| discovery_migrate.py        | on_message         | (client, userdata, msg)                                | [x]         |       |
| smoke_handlers.py           | on_connect         | (client, userdata, flags, rc, properties=None)         | [x]         |       |
| smoke_handlers.py           | on_message         | (client, userdata, msg)                                | [x]         |       |
| ...                         | ...                | ...                                                    | [ ]         |       |

## Instructions
- For each file and callback, verify the function signature matches the required VERSION2 format.
- Mark Status as [x] when verified and compliant.
- Add notes for any deviations, exceptions, or rationale for fallback to VERSION1.
- Update this matrix after every migration or audit.
