from __future__ import annotations

import argparse
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import warnings
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

from src.security.auth import AuthenticatedUser, AuthenticationError, authenticate_bearer, validate_auth_configuration
from src.security.network_policy import UnsafeURLError, validate_public_url
from src.security.rate_limit import SlidingWindowRateLimiter


ROOT_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
GENERATED_DIR = ROOT_DIR / "shared" / "generated"
DETAILED_REPORT_DIR = GENERATED_DIR / "audit-report"
GTM_REPORT_DIR = GENERATED_DIR / "gtm-report"
DETAILED_VERCEL_DIR = GENERATED_DIR / "vercel-audit-report"
GTM_VERCEL_DIR = GENERATED_DIR / "vercel-gtm-report"
SCREENSHOT_AUDIT_DIR = GENERATED_DIR / "screenshot-audits"
MOBILE_AUDIT_DIR = GENERATED_DIR / "mobile-audits"
FIGMA_AUDIT_DIR = GENERATED_DIR / "figma-audits"
OWNERSHIP_DIR = GENERATED_DIR / "ownership"
JOB_ARTIFACT_DIR = GENERATED_DIR / "job-artifacts"

STAGE_RE = re.compile(r"\[(?P<current>\d+)/(?P<total>\d+)\]\s*(?P<label>.+)")
SCREENSHOT_LOG_RE = re.compile(r"screenshot saved:\s*(?P<path>.+)$", re.IGNORECASE)
IMAGE_FORMATS = {"PNG": ("image/png", ".png"), "JPEG": ("image/jpeg", ".jpg"), "WEBP": ("image/webp", ".webp")}
FOREGROUND_ACTIVITY_RE = re.compile(r"(?P<package>[A-Za-z0-9._$]+)/(?P<activity>[A-Za-z0-9._$/-]+)")
ANDROID_SYSTEM_PACKAGE_PREFIXES = (
    "android",
    "com.android.",
    "com.google.android.",
    "com.google.android.apps.nexuslauncher",
    "com.google.android.inputmethod",
)

load_dotenv(ROOT_DIR / ".env")

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
JOB_PROCESSES: dict[str, subprocess.Popen[str]] = {}
JOB_PROCESSES_LOCK = threading.Lock()
CANCELLED_RETURN_CODE = -999
RATE_LIMITER = SlidingWindowRateLimiter()


def _env_positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return value


MAX_JSON_BODY_BYTES = _env_positive_int("UX_MAX_JSON_BODY_BYTES", 1_048_576)
MAX_MULTIPART_BODY_BYTES = _env_positive_int("UX_MAX_MULTIPART_BODY_BYTES", 26_214_400)
MAX_UPLOAD_COUNT = _env_positive_int("UX_MAX_UPLOAD_COUNT", 10)
MAX_UPLOAD_BYTES = _env_positive_int("UX_MAX_UPLOAD_BYTES", 8_388_608)
MAX_IMAGE_DIMENSION = _env_positive_int("UX_MAX_IMAGE_DIMENSION", 8_000)
MAX_IMAGE_PIXELS = _env_positive_int("UX_MAX_IMAGE_PIXELS", 40_000_000)


def _adb_stdout(*args: str, **kwargs: Any) -> str:
    from src.mobile_audit.device_manager import adb_stdout

    return adb_stdout(*args, **kwargs)


def _resolve_adb_executable() -> str:
    from src.mobile_audit.device_manager import resolve_adb_executable

    return resolve_adb_executable()


@dataclass
class UploadedFile:
    filename: str
    data: bytes
    content_type: str


@dataclass
class MultipartForm:
    fields: dict[str, list[str]] = field(default_factory=dict)
    files: dict[str, list[UploadedFile]] = field(default_factory=dict)

    def getfirst(self, name: str, default: str = "") -> str:
        values = self.fields.get(name) or []
        return values[0] if values else default

    def getfiles(self, name: str) -> list[UploadedFile]:
        return list(self.files.get(name) or [])


def _env_host(default: str = "0.0.0.0") -> str:
    return str(os.getenv("HOST") or default).strip() or default


def _env_port(default: int = 8787) -> int:
    raw = str(os.getenv("PORT") or default).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _cors_allowed_origins() -> set[str]:
    origins: set[str] = set()
    raw = os.getenv("UX_CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8787,http://localhost:8787")
    for value in raw.split(","):
        candidate = value.strip()
        parsed = urlparse(candidate)
        if (
            parsed.scheme in {"http", "https"}
            and parsed.netloc
            and not parsed.path.rstrip("/")
            and not parsed.query
            and not parsed.fragment
            and candidate == f"{parsed.scheme}://{parsed.netloc}"
        ):
            origins.add(candidate)
    return origins


def _now() -> float:
    return time.time()


def _new_job(url: str, mode: str) -> dict[str, Any]:
    job = {
        "id": uuid.uuid4().hex[:12],
        "type": "website",
        "surfaceType": "website",
        "inputType": "url",
        "url": url,
        "mode": mode,
        "status": "queued",
        "stage": "Queued",
        "progress": 0,
        "logs": [],
        "resultUrl": "",
        "error": "",
        "cancelRequested": False,
        "createdAt": _now(),
        "updatedAt": _now(),
    }
    return job


def _normalize_surface_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return "mobile_app" if normalized in {"mobile", "mobile_app", "app", "mobile-app"} else "website"


def _new_screenshot_job(site_name: str, screenshot_paths: list[Path], screenshot_labels: list[str], surface_type: str = "website") -> dict[str, Any]:
    normalized_surface = _normalize_surface_type(surface_type)
    return {
        "id": uuid.uuid4().hex[:12],
        "type": "mobile" if normalized_surface == "mobile_app" else "website",
        "surfaceType": normalized_surface,
        "inputType": "screenshot",
        "url": "",
        "mode": "gtm",
        "siteName": site_name,
        "screenshotPaths": [str(path) for path in screenshot_paths],
        "screenshotLabels": screenshot_labels,
        "previewImagePath": str(screenshot_paths[0]) if screenshot_paths else "",
        "status": "queued",
        "stage": "Queued",
        "progress": 0,
        "logs": [],
        "resultUrl": "",
        "error": "",
        "cancelRequested": False,
        "createdAt": _now(),
        "updatedAt": _now(),
    }


def _new_mobile_job(
    app_label: str,
    app_package: str,
    app_activity: str,
    appium_url: str,
    device_name: str,
    platform_version: str,
    udid: str,
) -> dict[str, Any]:
    return {
        "id": uuid.uuid4().hex[:12],
        "type": "mobile",
        "surfaceType": "mobile_app",
        "inputType": "interactive",
        "url": "",
        "mode": "interactive",
        "appLabel": app_label,
        "appPackage": app_package,
        "appActivity": app_activity,
        "appiumUrl": appium_url,
        "deviceName": device_name,
        "platformVersion": platform_version,
        "udid": udid,
        "status": "queued",
        "stage": "Queued",
        "progress": 0,
        "logs": [],
        "resultUrl": "",
        "outputDir": "",
        "error": "",
        "cancelRequested": False,
        "createdAt": _now(),
        "updatedAt": _now(),
    }


def _new_figma_job(figma_url: str) -> dict[str, Any]:
    return {
        "id": uuid.uuid4().hex[:12],
        "type": "figma",
        "surfaceType": "figma",
        "inputType": "url",
        "url": figma_url,
        "mode": "figma",
        "status": "queued",
        "stage": "Queued",
        "progress": 0,
        "logs": [],
        "resultUrl": "",
        "outputDir": "",
        "error": "",
        "cancelRequested": False,
        "createdAt": _now(),
        "updatedAt": _now(),
    }


def _snapshot_job(job: dict[str, Any]) -> dict[str, Any]:
    safe = dict(job)
    safe.pop("ownerEmail", None)
    safe.pop("ownerRole", None)
    safe.pop("ownerId", None)
    safe["logs"] = list(job.get("logs", []))[-200:]
    return safe


def _ownership_path(job_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise ValueError("Invalid audit identifier.")
    return OWNERSHIP_DIR / f"{job_id}.json"


def _assign_owner(job: dict[str, Any], user: AuthenticatedUser) -> None:
    job["ownerId"] = user.id
    job["ownerRole"] = user.role
    job["ownerEmail"] = user.email


def _persist_ownership(job: dict[str, Any]) -> None:
    path = _ownership_path(str(job.get("id") or ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(
            {
                "jobId": job["id"],
                "ownerId": job.get("ownerId"),
                "ownerRole": job.get("ownerRole"),
                "createdAt": job.get("createdAt"),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def _owned_job(job_id: str, user: AuthenticatedUser) -> dict[str, Any] | None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or not job.get("ownerId"):
            return None
        if str(job.get("ownerId")) != user.id:
            return None
        return job


def _persisted_owner_id(job_id: str) -> str:
    try:
        payload = json.loads(_ownership_path(job_id).read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    if str(payload.get("jobId") or "") != job_id:
        return ""
    return str(payload.get("ownerId") or "").strip()


def _user_owns_resource(job_id: str, user: AuthenticatedUser) -> bool:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is not None:
            return bool(job.get("ownerId")) and str(job.get("ownerId")) == user.id
    return _persisted_owner_id(job_id) == user.id


def _artifact_job_id(target: Path) -> str:
    try:
        relative = target.resolve(strict=True).relative_to(GENERATED_DIR.resolve())
    except (ValueError, FileNotFoundError):
        return ""
    if target.is_symlink():
        return ""
    for part in relative.parts:
        if re.fullmatch(r"[a-f0-9]{12}", part) and _ownership_path(part).is_file():
            return part
    return ""


def _snapshot_for_request(job: dict[str, Any], handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    payload = _snapshot_job(job)
    job_id = str(payload.get("id") or "").strip()
    result_url = str(payload.get("resultUrl") or "")
    if (
        job_id
        and payload.get("status") == "completed"
        and str(payload.get("stage") or "") == "Ready for local review"
        and not result_url.startswith("/audits/")
    ):
        local_path = f"/audits/{quote(job_id, safe='')}/"
        if _local_audit_static_path(local_path):
            payload["resultUrl"] = local_path
    result_url = str(payload.get("resultUrl") or "")
    if result_url.startswith("/"):
        payload["localResultUrl"] = result_url
    return payload


def _append_log(job_id: str, line: str) -> None:
    clean_line = line.rstrip()
    if not clean_line:
        return
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job["logs"].append(clean_line)
        job["updatedAt"] = _now()
        match = STAGE_RE.search(clean_line)
        if match:
            current = int(match.group("current"))
            total = int(match.group("total"))
            label = match.group("label").strip().strip(".")
            job["stage"] = label
            job["progress"] = max(job.get("progress", 0), round((current - 1) / max(total, 1) * 85))
        screenshot_match = SCREENSHOT_LOG_RE.search(clean_line)
        if screenshot_match:
            preview_path = _isolate_preview_artifact(job_id, screenshot_match.group("path").strip())
            if preview_path:
                job["previewImagePath"] = str(preview_path)


def _isolate_preview_artifact(job_id: str, raw_path: str) -> Path | None:
    source = Path(raw_path)
    source = source if source.is_absolute() else ROOT_DIR / source
    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to((ROOT_DIR / "shared" / "output" / "screenshots").resolve())
    except (ValueError, FileNotFoundError):
        return None
    if resolved.is_symlink() or resolved.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return None
    target_dir = JOB_ARTIFACT_DIR / job_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"preview{resolved.suffix.lower()}"
    shutil.copy2(resolved, target)
    return target


def _set_job(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job.update(updates)
        job["updatedAt"] = _now()


def _get_job_status(job_id: str) -> str:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return ""
        return str(job.get("status") or "")


def _is_cancel_requested(job_id: str) -> bool:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        return bool(job and job.get("cancelRequested"))


def _mark_job_cancelled(job_id: str) -> None:
    _set_job(
        job_id,
        status="cancelled",
        stage="Audit stopped",
        progress=100,
        error="Audit stopped by user.",
        cancelRequested=True,
    )


def _finish_if_cancelled(job_id: str) -> bool:
    if _is_cancel_requested(job_id) or _get_job_status(job_id) == "cancelled":
        _mark_job_cancelled(job_id)
        return True
    return False


def _derive_mobile_failure_error(job_id: str, exit_code: int) -> str:
    with JOBS_LOCK:
        job = JOBS.get(job_id) or {}
        logs = [str(line or "") for line in job.get("logs", [])]

    combined = "\n".join(logs)
    if "Neither ANDROID_HOME nor ANDROID_SDK_ROOT environment variable was exported" in combined:
        return (
            "Mobile app audit failed because the Appium process does not have "
            "ANDROID_HOME or ANDROID_SDK_ROOT configured. Restart Appium after "
            "exporting your Android SDK path."
        )
    if "adb could not be resolved" in combined or "adb was not found on PATH" in combined:
        return (
            "Mobile app audit failed because adb could not be resolved. Install Android "
            "platform-tools and make adb available to both the backend and the Appium process."
        )
    if "Appium session creation failed" in combined:
        return (
            f"Mobile app audit failed with exit code {exit_code} during Appium session creation. "
            "Check the Appium server, emulator/device availability, and app package/activity."
        )
    return (
        f"Mobile app audit failed with exit code {exit_code}. "
        "Check that Appium is running, the Android emulator/device is available, "
        "and the target app package/activity are correct."
    )


def _derive_website_pipeline_failure_error(job_id: str, exit_code: int) -> str:
    with JOBS_LOCK:
        job = JOBS.get(job_id) or {}
        logs = [str(line or "") for line in job.get("logs", [])]

    combined = "\n".join(logs)
    if "unable to verify the first certificate" in combined.lower():
        return (
            "Audit content was generated, but Vercel deployment failed because the Vercel CLI "
            "could not verify the TLS certificate. Restart the server with the latest code; the "
            "pipeline now keeps the local packaged report instead of failing the audit."
        )
    if "Crawler failed for this website" in combined:
        return "Website crawl failed. Check that the URL is reachable and not blocking automated browsers."
    if "Pipeline failed:" in combined:
        tail = [line.strip() for line in logs[-40:] if line.strip()]
        generic_process_exit = re.compile(r"(?:python(?:\.exe)?|Scripts\\python\.exe).*exited with code \d+", re.I)
        noisy_stage = re.compile(r"^\[\d+/\d+\]\s+|^Pipeline failed:$", re.I)
        details = [
            line
            for line in tail
            if not generic_process_exit.search(line)
            and not noisy_stage.search(line)
            and not line.startswith("$ ")
        ]
        detail = " | ".join(details[-4:]) if details else (tail[-1] if tail else "")
        if detail:
            return f"Audit pipeline failed with exit code {exit_code}: {detail}"
    return f"Audit pipeline failed with exit code {exit_code}."


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            process.wait(timeout=5)
            return
        except Exception:
            pass

    try:
        process.terminate()
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        return

    try:
        process.kill()
    except Exception:
        pass


def _cancel_job(job_id: str) -> tuple[dict[str, Any] | None, bool]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return None, False
        status = str(job.get("status") or "")
        if status not in {"queued", "running"}:
            return _snapshot_job(job), False
        job["cancelRequested"] = True
        job["status"] = "cancelled"
        job["stage"] = "Stopping audit"
        job["progress"] = 100
        job["error"] = "Audit stopped by user."
        job["updatedAt"] = _now()

    with JOB_PROCESSES_LOCK:
        process = JOB_PROCESSES.get(job_id)
    if process:
        _terminate_process(process)

    with JOBS_LOCK:
        return _snapshot_job(JOBS[job_id]), True


def _validate_url(value: str) -> str:
    url = value.strip()
    if not url:
        raise ValueError("Website URL is required.")
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        url = f"https://{url}"
    try:
        return validate_public_url(url).url
    except UnsafeURLError as exc:
        raise ValueError(str(exc)) from exc


def _validate_figma_url(value: str) -> str:
    figma_url = value.strip()
    if not figma_url:
        raise ValueError("Figma URL is required.")
    if not re.match(r"^https?://", figma_url, flags=re.IGNORECASE):
        figma_url = f"https://{figma_url}"
    parsed = urlparse(figma_url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {"figma.com", "www.figma.com"}:
        raise ValueError("Enter a valid Figma URL, for example https://www.figma.com/design/FILEKEY/Project.")
    if not re.search(r"/(file|design|proto|board)/[A-Za-z0-9]+", parsed.path):
        raise ValueError("Enter a Figma file, design, proto, or board URL.")
    return figma_url


def _trusted_appium_url(submitted: str) -> str:
    configured = (os.getenv("APPIUM_SERVER_URL") or "http://127.0.0.1:4723").strip().rstrip("/")
    parsed = urlparse(configured)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("APPIUM_SERVER_URL is invalid.")
    candidate = str(submitted or configured).strip().rstrip("/")
    if candidate != configured:
        raise ValueError("The Appium server URL is controlled by server configuration.")
    return configured


def _validate_required_text(value: str, field_label: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        raise ValueError(f"{field_label} is required.")
    return clean


def _friendly_app_label(package_name: str, activity_name: str = "") -> str:
    package_tail = str(package_name or "").strip().split(".")[-1]
    activity_tail = str(activity_name or "").strip().split("/")[-1].split(".")[-1]
    generic_activity_names = {"", "mainactivity", "launcheractivity", "splashactivity"}
    raw = package_tail if activity_tail.lower() in generic_activity_names else activity_tail or package_tail or "Android App Audit"
    raw = raw.replace("_", " ").replace("-", " ").strip()
    if not raw:
        return "Android App Audit"
    if raw.lower() == "mymg":
        return "MyMG"
    return " ".join(part.capitalize() for part in re.split(r"\s+", raw))


def _is_android_system_package(package_name: str) -> bool:
    clean = str(package_name or "").strip().lower()
    if not clean:
        return True
    return any(clean == prefix.rstrip(".") or clean.startswith(prefix) for prefix in ANDROID_SYSTEM_PACKAGE_PREFIXES)


def _find_launchable_app_for_package(launchable_apps: list[dict[str, str]], package_name: str) -> dict[str, str] | None:
    clean_package = str(package_name or "").strip()
    if not clean_package:
        return None
    for app in launchable_apps:
        if str(app.get("appPackage") or "").strip() == clean_package:
            return app
    return None


def _first_user_launchable_app(launchable_apps: list[dict[str, str]]) -> dict[str, str] | None:
    for app in launchable_apps:
        if not _is_android_system_package(str(app.get("appPackage") or "")):
            return app
    return launchable_apps[0] if launchable_apps else None


def _parse_adb_devices(raw_output: str) -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    for line in (raw_output or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("list of devices"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        extras = {token.split(":", 1)[0]: token.split(":", 1)[1] for token in parts[2:] if ":" in token}
        devices.append(
            {
                "udid": serial,
                "state": state,
                "model": extras.get("model", "").replace("_", " "),
                "device": extras.get("device", "").replace("_", " "),
                "product": extras.get("product", "").replace("_", " "),
            }
        )
    return devices


def _foreground_activity(adb_path: str, udid: str = "") -> tuple[str, str]:
    dumps = ""
    for command in (
        ("shell", "dumpsys", "activity", "activities"),
        ("shell", "dumpsys", "window", "windows"),
    ):
        try:
            dumps = _adb_stdout(*command, udid=udid or None, timeout_ms=15000, adb_path=adb_path)
        except Exception:
            dumps = ""
        if not dumps:
            continue
        for line in dumps.splitlines():
            if not any(token in line for token in ("mResumedActivity", "topResumedActivity", "mFocusedApp", "mCurrentFocus")):
                continue
            match = FOREGROUND_ACTIVITY_RE.search(line)
            if match:
                return match.group("package"), match.group("activity")
    return "", ""


def _launchable_apps(adb_path: str, udid: str = "") -> list[dict[str, str]]:
    commands = [
        ("shell", "cmd", "package", "query-activities", "--brief", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER"),
        ("shell", "cmd", "package", "query-activities", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER"),
    ]
    output = ""
    for command in commands:
        try:
            output = _adb_stdout(*command, udid=udid or None, timeout_ms=20000, adb_path=adb_path)
        except Exception:
            output = ""
        if output:
            break

    apps: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in output.splitlines():
        stripped = line.strip()
        if "/" not in stripped:
            continue
        match = FOREGROUND_ACTIVITY_RE.search(stripped)
        if not match:
            continue
        package_name = match.group("package")
        activity_name = match.group("activity")
        key = (package_name, activity_name)
        if key in seen:
            continue
        seen.add(key)
        apps.append(
            {
                "appPackage": package_name,
                "appActivity": activity_name,
                "appLabel": _friendly_app_label(package_name, activity_name),
            }
        )
    apps.sort(key=lambda item: (item["appLabel"].lower(), item["appPackage"].lower()))
    return apps


def _mobile_discovery_payload() -> dict[str, Any]:
    adb_path = _resolve_adb_executable()
    devices = _parse_adb_devices(_adb_stdout("devices", "-l", timeout_ms=10000, adb_path=adb_path))
    online_devices = [device for device in devices if device.get("state") == "device"]
    selected = online_devices[0] if online_devices else (devices[0] if devices else None)
    selected_udid = str((selected or {}).get("udid") or "")

    model = ""
    platform_version = ""
    current_package = ""
    current_activity = ""
    current_app: dict[str, str] | None = None
    launchable_apps: list[dict[str, str]] = []
    warnings: list[str] = []

    if selected_udid:
        try:
            model = _adb_stdout("shell", "getprop", "ro.product.model", udid=selected_udid, timeout_ms=8000, adb_path=adb_path)
        except Exception as exc:
            warnings.append(f"Unable to read device model: {exc}")
        try:
            platform_version = _adb_stdout("shell", "getprop", "ro.build.version.release", udid=selected_udid, timeout_ms=8000, adb_path=adb_path)
        except Exception as exc:
            warnings.append(f"Unable to read platform version: {exc}")
        try:
            current_package, current_activity = _foreground_activity(adb_path, udid=selected_udid)
        except Exception as exc:
            warnings.append(f"Unable to detect the foreground app: {exc}")
        try:
            launchable_apps = _launchable_apps(adb_path, udid=selected_udid)
        except Exception as exc:
            warnings.append(f"Unable to list launchable apps: {exc}")

    if current_package and not _is_android_system_package(current_package):
        launchable_current = _find_launchable_app_for_package(launchable_apps, current_package)
        if launchable_current:
            current_app = launchable_current
        elif current_activity:
            current_app = {
                "appPackage": current_package,
                "appActivity": current_activity,
                "appLabel": _friendly_app_label(current_package, current_activity),
            }
            warnings.append(
                "The foreground app was detected, but no launcher activity was found for it. "
                "If session creation fails, choose a detected launchable app manually."
            )
            launchable_apps = [current_app, *launchable_apps]

    if not current_app:
        current_app = _first_user_launchable_app(launchable_apps)

    return {
        "adbPath": adb_path,
        "devices": devices,
        "selectedDevice": {
            "udid": selected_udid,
            "deviceName": model or str((selected or {}).get("model") or (selected or {}).get("device") or "Android Device"),
            "platformVersion": platform_version,
            "state": str((selected or {}).get("state") or ""),
        } if selected else None,
        "defaults": {
            "appiumUrl": "http://127.0.0.1:4723",
            "deviceName": model or str((selected or {}).get("model") or (selected or {}).get("device") or "Android Emulator"),
            "platformVersion": platform_version,
            "udid": selected_udid,
        },
        "currentApp": current_app,
        "launchableApps": launchable_apps[:80],
        "warnings": warnings,
    }


def _validated_image(item: UploadedFile) -> tuple[bytes, str]:
    if not item.data or len(item.data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Each screenshot must be between 1 byte and {MAX_UPLOAD_BYTES} bytes.")
    if item.content_type.lower() not in {value[0] for value in IMAGE_FORMATS.values()}:
        raise ValueError("Only PNG, JPEG, and WebP screenshots are accepted.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(item.data)) as image:
                detected = str(image.format or "").upper()
                if detected not in IMAGE_FORMATS:
                    raise ValueError("Only PNG, JPEG, and WebP screenshots are accepted.")
                expected_mime, extension = IMAGE_FORMATS[detected]
                if item.content_type.lower() != expected_mime:
                    raise ValueError("The screenshot MIME type does not match its file signature.")
                if getattr(image, "is_animated", False) or int(getattr(image, "n_frames", 1)) != 1:
                    raise ValueError("Animated screenshots are not supported.")
                width, height = image.size
                if width <= 0 or height <= 0 or width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    raise ValueError("Screenshot dimensions exceed the configured limit.")
                if width * height > MAX_IMAGE_PIXELS:
                    raise ValueError("Screenshot pixel count exceeds the configured limit.")
                image.verify()
            with Image.open(io.BytesIO(item.data)) as decoded:
                decoded.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError("The screenshot is malformed or unsafe.") from exc
    return item.data, extension


def _read_multipart_form(handler: BaseHTTPRequestHandler) -> MultipartForm:
    content_type = handler.headers.get("Content-Type", "")
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if not content_type.startswith("multipart/form-data"):
        raise ValueError("Request must use multipart/form-data.")
    if length <= 0:
        raise ValueError("Multipart request body is empty.")
    if length > MAX_MULTIPART_BODY_BYTES:
        raise ValueError(f"Multipart request exceeds the {MAX_MULTIPART_BODY_BYTES}-byte limit.")

    raw_body = handler.rfile.read(length)
    message_bytes = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n"
        "\r\n"
    ).encode("utf-8") + raw_body
    message = BytesParser(policy=policy.default).parsebytes(message_bytes)
    if not message.is_multipart():
        raise ValueError("Multipart request body could not be parsed.")

    form = MultipartForm()
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename:
            form.files.setdefault(name, []).append(
                UploadedFile(filename=filename, data=payload, content_type=str(part.get_content_type() or ""))
            )
            continue
        charset = part.get_content_charset() or "utf-8"
        form.fields.setdefault(name, []).append(payload.decode(charset, errors="replace"))
    return form


def _field_value(form: MultipartForm, name: str, default: str = "") -> str:
    value = form.getfirst(name, default)
    return str(value or default).strip()


def _field_json_array(form: MultipartForm, name: str) -> list[str]:
    raw = _field_value(form, name, "[]")
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item or "").strip() for item in parsed]


def _field_items(form: MultipartForm, name: str) -> list[UploadedFile]:
    return [item for item in form.getfiles(name) if item.filename]


def _save_screenshot_uploads(form: MultipartForm, job_id: str, labels: list[str]) -> list[Path]:
    upload_dir = SCREENSHOT_AUDIT_DIR / job_id / "uploads"
    files = _field_items(form, "screenshots")
    if not files:
        raise ValueError("Upload at least one screenshot image.")
    if len(files) > MAX_UPLOAD_COUNT:
        raise ValueError(f"No more than {MAX_UPLOAD_COUNT} screenshots may be uploaded.")
    upload_dir.mkdir(parents=True, exist_ok=False)
    saved_paths: list[Path] = []
    try:
        for index, item in enumerate(files, start=1):
            data, extension = _validated_image(item)
            target = upload_dir / f"{index:03d}-{uuid.uuid4().hex}{extension}"
            target.write_bytes(data)
            saved_paths.append(target)
        return saved_paths
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise


def _artifact_url_for_path(path: Path) -> str:
    target = path if path.is_absolute() else ROOT_DIR / path
    try:
        rel = target.resolve().relative_to(ROOT_DIR.resolve())
    except ValueError:
        return ""
    return f"/artifacts/{quote(rel.as_posix(), safe='/')}"


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _contains_symlink(path: Path, root: Path) -> bool:
    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError:
        return True
    current = root.absolute()
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _packaged_report_url(static_dir: Path) -> str:
    audit_indexes = sorted(
        (static_dir / "audits").glob("*/index.html"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if audit_indexes:
        return f"/audits/{quote(audit_indexes[0].parent.name, safe='')}/"
    index_path = static_dir / "index.html"
    return _artifact_url_for_path(index_path) if index_path.exists() else ""


def _package_local_report(report_dir: Path, vercel_dir: Path, job_id: str) -> str:
    from src.gtm_audit.vercel_static_deploy import package_report_for_vercel

    package_report_for_vercel(report_dir, vercel_dir, audit_slug=job_id)
    return _packaged_report_url(vercel_dir)


def _candidate_audit_static_roots() -> list[Path]:
    roots = [
        GTM_VERCEL_DIR,
        DETAILED_VERCEL_DIR,
        GENERATED_DIR / "vercel-audit-report",
    ]
    for parent, pattern in (
        (FIGMA_AUDIT_DIR, "*/vercel-figma-report"),
        (SCREENSHOT_AUDIT_DIR, "*/vercel-gtm-report"),
        (MOBILE_AUDIT_DIR, "*/vercel-gtm-report"),
    ):
        if parent.exists():
            roots.extend(parent.glob(pattern))
    return roots


def _local_audit_static_path(request_path: str) -> Path | None:
    rel = unquote(request_path.lstrip("/")).replace("\\", "/").strip("/")
    parts = [part for part in rel.split("/") if part]
    if len(parts) < 2 or parts[0] != "audits":
        return None
    if len(parts) == 2:
        rel = f"audits/{parts[1]}/index.html"

    for root in _candidate_audit_static_roots():
        candidate = root / rel
        if _contains_symlink(candidate, root):
            continue
        target = candidate.resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            continue
        if target.exists() and target.is_file():
            return target
    return None


def _publish_job_report(job: dict[str, Any]) -> str:
    if str(job.get("status") or "") != "completed":
        raise ValueError("Only completed audits can be published.")
    job_id = str(job.get("id") or "")
    index_path = _local_audit_static_path(f"/audits/{job_id}/")
    if not index_path or index_path.is_symlink() or index_path.parent.name != job_id:
        raise ValueError("The immutable machine-generated report is unavailable.")
    from src.gtm_audit.vercel_static_deploy import publish_selected_report

    return publish_selected_report(index_path.parent)


def _figma_run_status_error(output_dir: Path) -> str:
    status_path = output_dir / "data" / "run_status.json"
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    error = str(payload.get("error") or "").strip()
    if error:
        return error
    stages = payload.get("stages")
    if isinstance(stages, list):
        for stage in reversed(stages):
            if isinstance(stage, dict) and stage.get("error"):
                return str(stage.get("error") or "").strip()
    return ""


def _update_job_progress_from_output(job_id: str, line: str) -> None:
    text = (line or "").strip()
    if not text:
        return

    markers = [
        ("[1/5] Running crawler", "Crawling website", 8),
        ("[2/5] Running page audit", "Opening pages", 24),
        ("[3/5] Generating checks JSON", "Extracting UI evidence", 58),
        ("[4/5] Generating GTM", "Building audit report", 72),
        ("[4/5] Exporting workbook", "Building audit report", 72),
        ("[4/5] Workbook export skipped", "Building audit report", 72),
        ("[5/5] Generating", "Building audit report", 82),
        ("[1/5] Running Figma audit pipeline", "Fetching Figma design", 8),
        ("[2/5] Capturing real Figma screenshots", "Capturing Figma evidence", 42),
        ("[3/5] Refreshing Figma evidence", "Validating Figma evidence", 58),
        ("[4/5] Generating editable Figma audit report", "Building editable Figma report", 74),
        ("[5/5] Figma audit report ready", "Preparing local report", 88),
        ("Deploying report", "Preparing local report", 90),
    ]
    for marker, stage, progress in markers:
        if marker in text:
            _set_job(job_id, stage=stage, progress=progress)
            return

    match = re.search(r"(?:Page|\[START|\[DONE)\s+(\d+)\s*/\s*(\d+)", text, re.I)
    if match:
        current = max(1, int(match.group(1)))
        total = max(1, int(match.group(2)))
        progress = 24 + round(min(current, total) / total * 30)
        _set_job(job_id, stage=f"Opening pages ({current}/{total})", progress=progress)


def _run_command(job_id: str, command: list[str], *, stage: str, progress: int, env_overrides: dict[str, str] | None = None) -> int:
    if _finish_if_cancelled(job_id):
        return CANCELLED_RETURN_CODE

    _set_job(job_id, stage=stage, progress=progress)
    _append_log(job_id, f"$ {' '.join(command)}")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if env_overrides:
        env.update(env_overrides)
    process = subprocess.Popen(
        command,
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    with JOB_PROCESSES_LOCK:
        JOB_PROCESSES[job_id] = process
    try:
        assert process.stdout is not None
        for line in process.stdout:
            if _finish_if_cancelled(job_id):
                _terminate_process(process)
                return CANCELLED_RETURN_CODE
            _append_log(job_id, line)
            _update_job_progress_from_output(job_id, line)
        return_code = process.wait()
        if _finish_if_cancelled(job_id):
            return CANCELLED_RETURN_CODE
        return return_code
    finally:
        with JOB_PROCESSES_LOCK:
            if JOB_PROCESSES.get(job_id) is process:
                JOB_PROCESSES.pop(job_id, None)


def _report_paths_for_mode(mode: str) -> tuple[Path, Path]:
    if mode == "gtm":
        return GTM_REPORT_DIR, GTM_VERCEL_DIR
    return DETAILED_REPORT_DIR, DETAILED_VERCEL_DIR


def _run_audit_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        url = job["url"]
        mode = job["mode"]

    _set_job(job_id, status="running", stage="Starting audit", progress=2)
    pipeline_command = [
        sys.executable,
        "scripts/run_pipeline.py",
        url,
        "--mode",
        mode,
    ]
    if mode == "gtm" and _env_flag("GTM_SKIP_VISION", default=False):
        pipeline_command.append("--skip-vision")
    pipeline_code = _run_command(
        job_id,
        pipeline_command,
        stage="Running audit pipeline",
        progress=5,
        env_overrides={"GTM_AUTO_DEPLOY": "0", "GTM_DISABLE_VERCEL_DEPLOY": "1"},
    )
    if pipeline_code == CANCELLED_RETURN_CODE or _finish_if_cancelled(job_id):
        return
    if pipeline_code != 0:
        _set_job(
            job_id,
            status="failed",
            error=_derive_website_pipeline_failure_error(job_id, pipeline_code),
        )
        return

    if _finish_if_cancelled(job_id):
        return

    report_dir, vercel_dir = _report_paths_for_mode(mode)
    try:
        local_report_url = _package_local_report(report_dir, vercel_dir, job_id)
    except Exception as exc:
        _set_job(job_id, status="failed", error=f"Local editable report packaging failed: {exc}")
        return
    _set_job(
        job_id,
        status="completed",
        stage="Ready for local review",
        progress=100,
        resultUrl=local_report_url,
        error="",
    )


def _run_screenshot_audit_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        screenshot_paths = [Path(path) for path in job.get("screenshotPaths", [])]
        site_name = str(job.get("siteName") or "Screenshot Audit")
        screenshot_labels = [str(label).strip() for label in job.get("screenshotLabels", []) if str(label).strip()]
        surface_type = _normalize_surface_type(str(job.get("surfaceType") or "website"))

    if _env_flag("SCREENSHOT_AUDITS_DISABLED", default=False):
        _set_job(
            job_id,
            status="failed",
            error=(
                "Screenshot audits are disabled for this deployment. "
                "Deploy a compatible multimodal model backend first, then unset SCREENSHOT_AUDITS_DISABLED."
            ),
        )
        return

    job_dir = SCREENSHOT_AUDIT_DIR / job_id
    audit_json = job_dir / "screenshot_gtm_audit.json"
    report_dir = job_dir / "gtm-report"
    vercel_dir = job_dir / "vercel-gtm-report"
    surface_label = "mobile app screenshots" if surface_type == "mobile_app" else "website screenshots"

    _set_job(job_id, status="running", stage=f"Analyzing uploaded {surface_label}", progress=5)
    analysis_command = [
        sys.executable,
        "-m",
        "src.gtm_audit.generate_screenshot_gtm_audit",
        "--output",
        str(audit_json),
        "--site-name",
        site_name,
        "--surface-type",
        surface_type,
        "--screenshots",
        *[str(path) for path in screenshot_paths],
    ]
    if screenshot_labels:
        analysis_command.extend(["--screenshot-names-json", json.dumps(screenshot_labels, ensure_ascii=False)])
    analysis_code = _run_command(job_id, analysis_command, stage=f"Running {surface_label} GTM audit", progress=10)
    if analysis_code == CANCELLED_RETURN_CODE or _finish_if_cancelled(job_id):
        return
    if analysis_code != 0:
        _set_job(
            job_id,
            status="failed",
            error=f"{surface_label.title()} audit failed with exit code {analysis_code}.",
        )
        return

    report_code = _run_command(
        job_id,
        [
            sys.executable,
            "-m",
            "src.gtm_audit.generate_gtm_report",
            "--input",
            str(audit_json),
            "--output-dir",
            str(report_dir),
        ],
        stage=f"Generating {surface_label} report",
        progress=70,
    )
    if report_code == CANCELLED_RETURN_CODE or _finish_if_cancelled(job_id):
        return
    if report_code != 0:
        _set_job(job_id, status="failed", error=f"Report generation failed with exit code {report_code}.")
        return

    try:
        local_report_url = _package_local_report(report_dir, vercel_dir, job_id)
    except Exception as exc:
        _set_job(job_id, status="failed", error=f"Local editable report packaging failed: {exc}")
        return
    _set_job(
        job_id,
        status="completed",
        stage="Ready for local review",
        progress=100,
        resultUrl=local_report_url,
        error="",
    )


def _run_figma_audit_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        figma_url = str(job.get("url") or "").strip()

    if _env_flag("FIGMA_AUDITS_DISABLED", default=False):
        _set_job(
            job_id,
            status="failed",
            error="Figma audits are disabled for this deployment. Unset FIGMA_AUDITS_DISABLED to enable them.",
        )
        return

    output_dir = FIGMA_AUDIT_DIR / job_id
    report_dir = output_dir / "figma-report"
    vercel_dir = output_dir / "vercel-figma-report"

    _set_job(job_id, status="running", stage="Starting Figma audit", progress=2, outputDir=str(output_dir))
    audit_code = _run_command(
        job_id,
        [
            sys.executable,
            "-m",
            "src.figma_audit_runner",
            figma_url,
            "--job-id",
            job_id,
            "--output-root",
            str(FIGMA_AUDIT_DIR),
        ],
        stage="Running Figma audit pipeline",
        progress=5,
    )
    if audit_code == CANCELLED_RETURN_CODE or _finish_if_cancelled(job_id):
        return
    if audit_code != 0:
        run_error = _figma_run_status_error(output_dir)
        _set_job(
            job_id,
            status="failed",
            outputDir=str(output_dir),
            error=(
                run_error
                or (
                    f"Figma audit failed with exit code {audit_code}. "
                    "Check that FIGMA_TOKEN or FIGMA_TOKENS is configured and has access to the file."
                )
            ),
        )
        return

    try:
        local_report_url = _package_local_report(report_dir, vercel_dir, job_id)
    except Exception as exc:
        _set_job(job_id, status="failed", outputDir=str(output_dir), error=f"Local editable Figma report packaging failed: {exc}")
        return
    _set_job(
        job_id,
        status="completed",
        stage="Ready for local review",
        progress=100,
        outputDir=str(output_dir),
        resultUrl=local_report_url,
        error="",
    )


def _run_mobile_audit_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        app_label = str(job.get("appLabel") or "Android App Audit").strip() or "Android App Audit"
        app_package = str(job.get("appPackage") or "").strip()
        app_activity = str(job.get("appActivity") or "").strip()
        appium_url = str(job.get("appiumUrl") or "http://127.0.0.1:4723").strip() or "http://127.0.0.1:4723"
        device_name = str(job.get("deviceName") or "Android Emulator").strip() or "Android Emulator"
        platform_version = str(job.get("platformVersion") or "").strip()
        udid = str(job.get("udid") or "").strip()

    if _env_flag("MOBILE_AUDITS_DISABLED", default=False):
        _set_job(
            job_id,
            status="failed",
            error=(
                "Mobile live audits are disabled for this deployment. "
                "Run mobile audits on a machine with Appium and an attached device or emulator."
            ),
        )
        return

    output_dir = MOBILE_AUDIT_DIR / job_id
    _set_job(job_id, status="running", stage="Launching Android extraction", progress=5)
    command = [
        sys.executable,
        "-m",
        "src.mobile_audit.run_mobile_audit",
        "--job-id",
        job_id,
        "--output-root",
        str(MOBILE_AUDIT_DIR),
        "--app-package",
        app_package,
        "--app-activity",
        app_activity,
        "--appium-url",
        appium_url,
        "--device-name",
        device_name,
        "--full-reset",
        "--extract-only",
    ]
    if platform_version:
        command.extend(["--platform-version", platform_version])
    if udid:
        command.extend(["--udid", udid])

    _append_log(job_id, f"Preparing mobile audit for: {app_label}")
    exit_code = _run_command(job_id, command, stage="Running Android Block 1 extraction", progress=15)
    if exit_code == CANCELLED_RETURN_CODE or _finish_if_cancelled(job_id):
        return
    if exit_code != 0:
        _set_job(
            job_id,
            status="failed",
            error=_derive_mobile_failure_error(job_id, exit_code),
        )
        return

    if not output_dir.exists():
        _set_job(
            job_id,
            status="failed",
            error="Mobile extraction finished but the expected artifact directory was not created.",
        )
        return

    audit_json = output_dir / "mobile_gtm_audit.json"
    report_dir = output_dir / "gtm-report"
    vercel_dir = output_dir / "vercel-gtm-report"

    if not audit_json.exists():
        analysis_code = _run_command(
            job_id,
            [
                sys.executable,
                "-m",
                "src.mobile_audit.generate_mobile_audit",
                "--input-dir",
                str(output_dir),
                "--app-label",
                app_label,
                "--output",
                str(audit_json),
            ],
            stage="Analyzing live mobile UX/UI evidence",
            progress=62,
        )
        if analysis_code == CANCELLED_RETURN_CODE or _finish_if_cancelled(job_id):
            return
        if analysis_code != 0:
            _set_job(
                job_id,
                status="failed",
                outputDir=str(output_dir),
                error=f"Mobile extraction completed, but mobile audit analysis failed with exit code {analysis_code}.",
            )
            return

    if not (report_dir / "index.html").exists():
        report_code = _run_command(
            job_id,
            [
                sys.executable,
                "-m",
                "src.gtm_audit.generate_gtm_report",
                "--input",
                str(audit_json),
                "--output-dir",
                str(report_dir),
            ],
            stage="Generating live mobile audit report",
            progress=78,
        )
        if report_code == CANCELLED_RETURN_CODE or _finish_if_cancelled(job_id):
            return
        if report_code != 0:
            _set_job(job_id, status="failed", outputDir=str(output_dir), error=f"Mobile report generation failed with exit code {report_code}.")
            return

    try:
        local_report_url = _package_local_report(report_dir, vercel_dir, job_id)
    except Exception as exc:
        _set_job(job_id, status="failed", outputDir=str(output_dir), error=f"Local editable mobile report packaging failed: {exc}")
        return
    _set_job(
        job_id,
        status="completed",
        stage="Ready for local review",
        progress=100,
        outputDir=str(output_dir),
        resultUrl=local_report_url,
        error="",
    )


class AuditRequestHandler(BaseHTTPRequestHandler):
    server_version = "UXUIAuditUI/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        # Deliberately omit paths and headers so bearer tokens or sensitive URLs cannot enter logs.
        sys.stdout.write(f"{self.client_address[0]} - - [{self.log_date_time_string()}] request completed\n")

    def end_headers(self) -> None:
        origin = (self.headers.get("Origin") or "").strip()
        allowed_origins = _cors_allowed_origins()
        if origin and origin in allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        connect_sources = " ".join(sorted(allowed_origins))
        self.send_header("Content-Security-Policy", f"default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' {connect_sources}; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()

    def _authenticate(self) -> AuthenticatedUser | None:
        try:
            user = authenticate_bearer(self.headers)
        except AuthenticationError:
            self._discard_small_body()
            self._send_json({"error": "Authentication required."}, HTTPStatus.UNAUTHORIZED)
            return None
        source = self.client_address[0]
        limit = _env_positive_int("UX_RATE_LIMIT_PER_MINUTE", 120)
        allowed, retry = RATE_LIMITER.allow(f"all:{source}:{user.id}", limit)
        if not allowed:
            self._discard_small_body()
            self._send_json({"error": "Rate limit exceeded."}, HTTPStatus.TOO_MANY_REQUESTS, {"Retry-After": str(retry)})
            return None
        return user

    def _discard_small_body(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            return
        if 0 < length <= MAX_JSON_BODY_BYTES:
            self.rfile.read(length)

    def _require_owned_job(self, job_id: str, user: AuthenticatedUser) -> dict[str, Any] | None:
        job = _owned_job(job_id, user)
        if job is None:
            self._send_json({"error": "Audit job not found."}, HTTPStatus.NOT_FOUND)
        return job

    def _require_owned_resource(self, job_id: str, user: AuthenticatedUser) -> bool:
        if _user_owns_resource(job_id, user):
            return True
        self._send_json({"error": "Audit job not found."}, HTTPStatus.NOT_FOUND)
        return False

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK, headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        guessed_type, _encoding = mimetypes.guess_type(str(file_path))
        content_type = guessed_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type = f"{content_type}; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_path.stat().st_size))
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        with file_path.open("rb") as source:
            shutil.copyfileobj(source, self.wfile, length=64 * 1024)
        self.wfile.flush()

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > MAX_JSON_BODY_BYTES:
            if 0 < length <= MAX_MULTIPART_BODY_BYTES:
                self.rfile.read(length)
            raise ValueError(f"JSON request exceeds the {MAX_JSON_BODY_BYTES}-byte limit.")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object.")
        return data

    def do_OPTIONS(self) -> None:
        origin = (self.headers.get("Origin") or "").strip()
        allowed = _cors_allowed_origins()
        self.send_response(HTTPStatus.NO_CONTENT if origin in allowed else HTTPStatus.FORBIDDEN)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "service": "ux-ui-auditor",
                    "port": getattr(self.server, "server_port", None),
                }
            )
            return
        if parsed.path == "/" or parsed.path.startswith("/static/") or (not parsed.path.startswith(("/api/", "/audits/", "/artifacts/"))):
            if parsed.path == "/":
                self._send_file(STATIC_DIR / "index.html")
                return
            if parsed.path.startswith("/static/"):
                rel = unquote(parsed.path.removeprefix("/static/"))
                target = (STATIC_DIR / rel).resolve()
                if not _inside(target, STATIC_DIR):
                    self._send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
                    return
                self._send_file(target)
                return
            rel = unquote(parsed.path.lstrip("/"))
            target = (STATIC_DIR / rel).resolve()
            if rel and _inside(target, STATIC_DIR) and target.exists() and target.is_file():
                self._send_file(target)
                return
            self._send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
            return

        user = self._authenticate()
        if user is None:
            return
        if parsed.path == "/api/criteria":
            try:
                from src.gtm_audit.common import AUDIT_CRITERIA_CONFIG_PATH, current_audit_criteria_payload, load_audit_criteria_config

                load_audit_criteria_config()
                self._send_json(current_audit_criteria_payload(source="custom" if AUDIT_CRITERIA_CONFIG_PATH.exists() else "defaults"))
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if parsed.path == "/api/mobile/discovery":
            try:
                self._send_json(_mobile_discovery_payload())
            except Exception as exc:
                self._send_json(
                    {
                        "error": str(exc),
                        "devices": [],
                        "selectedDevice": None,
                        "defaults": {
                            "appiumUrl": "http://127.0.0.1:4723",
                            "deviceName": "Android Emulator",
                            "platformVersion": "",
                            "udid": "",
                        },
                        "currentApp": None,
                        "launchableApps": [],
                        "warnings": [],
                    },
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return
        if parsed.path.startswith("/api/audits/"):
            job_id = unquote(parsed.path.rsplit("/", 1)[-1])
            job = self._require_owned_job(job_id, user)
            if not job:
                return
            self._send_json(_snapshot_for_request(job, self))
            return
        if parsed.path.startswith("/audits/"):
            parts = [part for part in unquote(parsed.path).split("/") if part]
            if len(parts) < 2 or not self._require_owned_resource(parts[1], user):
                return
            target = _local_audit_static_path(parsed.path)
            if not target:
                self._send_json({"error": "Audit report not found."}, HTTPStatus.NOT_FOUND)
                return
            self._send_file(target)
            return
        if parsed.path.startswith("/artifacts/"):
            rel = unquote(parsed.path.removeprefix("/artifacts/")).replace("\\", "/").lstrip("/")
            candidate = ROOT_DIR / rel
            if _contains_symlink(candidate, ROOT_DIR):
                self._send_json({"error": "Audit job not found."}, HTTPStatus.NOT_FOUND)
                return
            target = candidate.resolve()
            job_id = _artifact_job_id(target)
            if not job_id or not self._require_owned_resource(job_id, user):
                return
            self._send_file(target)
            return
        self._send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
            return
        user = self._authenticate()
        if user is None:
            return

        if parsed.path.startswith("/api/audits/") and parsed.path.endswith("/cancel"):
            job_id = unquote(parsed.path.removeprefix("/api/audits/").removesuffix("/cancel").strip("/"))
            if not self._require_owned_job(job_id, user):
                return
            payload, _cancelled = _cancel_job(job_id)
            if not payload:
                self._send_json({"error": "Audit job not found."}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload)
            return

        if parsed.path.startswith("/api/audits/") and parsed.path.endswith("/publish"):
            job_id = unquote(parsed.path.removeprefix("/api/audits/").removesuffix("/publish").strip("/"))
            job = self._require_owned_job(job_id, user)
            if not job:
                return
            try:
                url = _publish_job_report(job)
                self._send_json({"url": url})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception:
                self._send_json({"error": "Report publication failed."}, HTTPStatus.BAD_GATEWAY)
            return

        if parsed.path == "/api/criteria":
            if not user.is_admin:
                self._send_json({"error": "Administrator access required."}, HTTPStatus.FORBIDDEN)
                return
            try:
                from src.gtm_audit.common import save_audit_criteria_payload

                data = self._read_json_body()
                self._send_json(save_audit_criteria_payload(data))
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if parsed.path == "/api/criteria/reset":
            if not user.is_admin:
                self._send_json({"error": "Administrator access required."}, HTTPStatus.FORBIDDEN)
                return
            try:
                from src.gtm_audit.common import reset_audit_criteria_payload

                self._send_json(reset_audit_criteria_payload())
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if parsed.path != "/api/audits":
            if parsed.path.startswith("/api/"):
                self._discard_small_body()
                self._send_json({"error": "API endpoint not found."}, HTTPStatus.NOT_FOUND)
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            create_limit = _env_positive_int("UX_AUDIT_CREATE_RATE_LIMIT_PER_MINUTE", 5)
            allowed, retry = RATE_LIMITER.allow(f"create:{self.client_address[0]}:{user.id}", create_limit)
            if not allowed:
                self._send_json({"error": "Audit creation rate limit exceeded."}, HTTPStatus.TOO_MANY_REQUESTS, {"Retry-After": str(retry)})
                return
            content_type = self.headers.get("Content-Type", "")
            if content_type.startswith("multipart/form-data"):
                form = _read_multipart_form(self)
                audit_type = _field_value(form, "auditType", "screenshot")
                if audit_type != "screenshot":
                    raise ValueError("Multipart upload is only supported for screenshot audits.")
                site_name = _field_value(form, "siteName", "Screenshot Audit") or "Screenshot Audit"
                surface_type = _normalize_surface_type(_field_value(form, "surfaceType", "website"))
                screenshot_labels = _field_json_array(form, "screenshotLabels")
                pending_job_id = uuid.uuid4().hex[:12]
                with JOBS_LOCK:
                    running = [job for job in JOBS.values() if job.get("status") in {"queued", "running"}]
                    if running:
                        self._send_json(
                            {"error": "Another audit is already running. Wait for it to finish before starting a new one."},
                            HTTPStatus.CONFLICT,
                        )
                        return
                pending_job = {"id": pending_job_id, "createdAt": _now()}
                _assign_owner(pending_job, user)
                _persist_ownership(pending_job)
                try:
                    screenshot_paths = _save_screenshot_uploads(form, pending_job_id, screenshot_labels)
                except Exception:
                    _ownership_path(pending_job_id).unlink(missing_ok=True)
                    raise
                screenshot_labels = [
                    (screenshot_labels[index] if index < len(screenshot_labels) and screenshot_labels[index] else path.stem)
                    for index, path in enumerate(screenshot_paths)
                ]
                with JOBS_LOCK:
                    job = _new_screenshot_job(site_name, screenshot_paths, screenshot_labels, surface_type=surface_type)
                    job["id"] = pending_job_id
                    _assign_owner(job, user)
                    _persist_ownership(job)
                    JOBS[job["id"]] = job
                worker = threading.Thread(target=_run_screenshot_audit_job, args=(job["id"],), daemon=True)
                worker.start()
                self._send_json(_snapshot_for_request(job, self), HTTPStatus.ACCEPTED)
                return

            data = self._read_json_body()
            audit_type = str(data.get("auditType") or "website")
            mode = str(data.get("mode") or "gtm").lower()
            with JOBS_LOCK:
                running = [job for job in JOBS.values() if job.get("status") in {"queued", "running"}]
                if running:
                    self._send_json(
                        {"error": "Another audit is already running. Wait for it to finish before starting a new one."},
                        HTTPStatus.CONFLICT,
                    )
                    return
                if audit_type == "website":
                    if mode not in {"detailed", "gtm"}:
                        raise ValueError("Audit mode must be either detailed or gtm.")
                    url = _validate_url(str(data.get("url") or ""))
                    job = _new_job(url, mode)
                    _assign_owner(job, user)
                    _persist_ownership(job)
                    JOBS[job["id"]] = job
                    worker = threading.Thread(target=_run_audit_job, args=(job["id"],), daemon=True)
                elif audit_type == "figma":
                    figma_url = _validate_figma_url(str(data.get("figmaUrl") or data.get("url") or ""))
                    job = _new_figma_job(figma_url)
                    _assign_owner(job, user)
                    _persist_ownership(job)
                    JOBS[job["id"]] = job
                    worker = threading.Thread(target=_run_figma_audit_job, args=(job["id"],), daemon=True)
                elif audit_type == "mobile":
                    app_label = str(data.get("appLabel") or "Android App Audit").strip() or "Android App Audit"
                    app_package = str(data.get("appPackage") or "").strip()
                    app_activity = str(data.get("appActivity") or "").strip()
                    appium_url = _trusted_appium_url(str(data.get("appiumUrl") or ""))
                    device_name = str(data.get("deviceName") or "Android Emulator").strip() or "Android Emulator"
                    platform_version = str(data.get("platformVersion") or "").strip()
                    udid = str(data.get("udid") or "").strip()

                    if not app_package or not app_activity:
                        discovery = _mobile_discovery_payload()
                        discovered_target = discovery.get("currentApp")
                        if not discovered_target:
                            launchable_apps = discovery.get("launchableApps") or []
                            discovered_target = launchable_apps[0] if launchable_apps else None
                        if isinstance(discovered_target, dict):
                            app_package = app_package or str(discovered_target.get("appPackage") or "").strip()
                            app_activity = app_activity or str(discovered_target.get("appActivity") or "").strip()
                            if app_label == "Android App Audit":
                                app_label = str(discovered_target.get("appLabel") or app_label).strip() or app_label
                        defaults = discovery.get("defaults") if isinstance(discovery, dict) else {}
                        if isinstance(defaults, dict):
                            device_name = device_name or str(defaults.get("deviceName") or "Android Emulator")
                            platform_version = platform_version or str(defaults.get("platformVersion") or "")
                            udid = udid or str(defaults.get("udid") or "")

                    app_package = _validate_required_text(app_package, "Android app package")
                    app_activity = _validate_required_text(app_activity, "Android app activity")
                    job = _new_mobile_job(
                        app_label=app_label,
                        app_package=app_package,
                        app_activity=app_activity,
                        appium_url=appium_url,
                        device_name=device_name,
                        platform_version=platform_version,
                        udid=udid,
                    )
                    _assign_owner(job, user)
                    _persist_ownership(job)
                    JOBS[job["id"]] = job
                    worker = threading.Thread(target=_run_mobile_audit_job, args=(job["id"],), daemon=True)
                else:
                    raise ValueError("Use multipart upload for screenshot audits. Supported JSON audit types are website, mobile, and figma.")
            worker.start()
            self._send_json(_snapshot_for_request(job, self), HTTPStatus.ACCEPTED)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception:
            self._send_json({"error": "Request could not be processed."}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local React audit launcher UI.")
    parser.add_argument("--host", default=_env_host())
    parser.add_argument("--port", type=int, default=_env_port())
    args = parser.parse_args()

    validate_auth_configuration(args.host)

    server = ThreadingHTTPServer((args.host, args.port), AuditRequestHandler)
    print(f"Audit launcher UI: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping audit launcher UI.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
