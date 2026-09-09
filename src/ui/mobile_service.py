"""Pure Android device-discovery normalization used by the UI server."""

from __future__ import annotations

import re


def friendly_app_label(package_name: str, activity_name: str = "") -> str:
    package_tail = str(package_name or "").strip().split(".")[-1]
    activity_tail = str(activity_name or "").strip().split("/")[-1].split(".")[-1]
    raw = package_tail if activity_tail.lower() in {"", "mainactivity", "launcheractivity", "splashactivity"} else activity_tail or package_tail or "Android App Audit"
    raw = raw.replace("_", " ").replace("-", " ").strip()
    if not raw:
        return "Android App Audit"
    return "MyMG" if raw.lower() == "mymg" else " ".join(part.capitalize() for part in re.split(r"\s+", raw))


def is_android_system_package(package_name: str, prefixes: tuple[str, ...]) -> bool:
    clean = str(package_name or "").strip().lower()
    return not clean or any(clean == prefix.rstrip(".") or clean.startswith(prefix) for prefix in prefixes)


def find_launchable_app(apps: list[dict[str, str]], package_name: str) -> dict[str, str] | None:
    return next((app for app in apps if package_name and str(app.get("appPackage") or "").strip() == package_name.strip()), None)


def parse_adb_devices(raw_output: str) -> list[dict[str, str]]:
    devices = []
    for line in (raw_output or "").splitlines():
        parts = line.strip().split()
        if len(parts) < 2 or line.strip().lower().startswith("list of devices"):
            continue
        extras = {token.split(":", 1)[0]: token.split(":", 1)[1] for token in parts[2:] if ":" in token}
        devices.append({"udid": parts[0], "state": parts[1], **{key: extras.get(key, "").replace("_", " ") for key in ("model", "device", "product")}})
    return devices
