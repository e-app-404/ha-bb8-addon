# bb8_core/version_probe.py

from importlib.metadata import PackageNotFoundError as E, version


def probe():
    pkgs = ("bleak", "paho-mqtt", "spherov2")
    out = []
    for p in pkgs:
        try:
            out.append({"pkg": p, "version": version(p)})
        except E:
            out.append({"pkg": p, "version": "missing"})
    return {"event": "version_probe", **{p["pkg"]: p["version"] for p in out}}
