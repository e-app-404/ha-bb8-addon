# bb8_core/version_probe.py

from importlib.metadata import PackageNotFoundError as E
from importlib.metadata import version


def probe():
    """Probes the versions of specified Python packages and returns their version information.

    Returns:
        dict: A dictionary containing the event name ("version_probe") and the version information
        for each package in the format {package_name: version}. If a package is missing, its version
        is set to "missing".

    """
    pkgs = ("bleak", "paho-mqtt", "spherov2")
    out = []
    for p in pkgs:
        try:
            out.append({"pkg": p, "version": version(p)})
        except E:
            out.append({"pkg": p, "version": "missing"})
    return {"event": "version_probe", **{p["pkg"]: p["version"] for p in out}}
