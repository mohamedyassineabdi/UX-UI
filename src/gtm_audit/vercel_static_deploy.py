from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import secrets
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Dict
from urllib.parse import quote, unquote, urlsplit


ROOT_DIR = Path(__file__).resolve().parents[2]
GENERATED_DIR = ROOT_DIR / "shared" / "generated"
DEFAULT_REPORT_DIR = GENERATED_DIR / "gtm-report"
DEFAULT_STATIC_DIR = GENERATED_DIR / "vercel-gtm-report"
LOCAL_REF_RE = re.compile(r'(?P<attr>src|href)="(?P<href>[^"]+)"')


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _safe_clear_dir(path: Path) -> None:
    resolved = path.resolve()
    if not _inside(resolved, GENERATED_DIR):
        raise RuntimeError(f"Refusing to clear non-generated directory: {resolved}")
    if resolved.exists():
        def _clear_readonly(func, failed_path, _exc_info):
            os.chmod(failed_path, stat.S_IWRITE)
            func(failed_path)

        shutil.rmtree(resolved, onerror=_clear_readonly)
    resolved.mkdir(parents=True, exist_ok=True)


def _is_external_or_special(href: str) -> bool:
    lowered = href.lower()
    return (
        not href
        or href.startswith("#")
        or lowered.startswith(("http://", "https://", "mailto:", "tel:", "data:", "javascript:"))
    )


def _asset_href_for_source(source: Path) -> str:
    try:
        rel = source.resolve().relative_to(ROOT_DIR.resolve())
    except ValueError:
        rel = Path(source.name)
    return quote((Path("assets") / rel).as_posix(), safe="/:#?&=%")


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return slug[:80] or "audit"


def _copy_report_with_assets(report_dir: Path, target_dir: Path) -> Path:
    report_dir = report_dir if report_dir.is_absolute() else ROOT_DIR / report_dir
    target_dir = target_dir if target_dir.is_absolute() else ROOT_DIR / target_dir
    index_path = report_dir / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"Report index.html not found: {index_path}")

    report_root = report_dir.resolve()
    for source in report_root.rglob("*"):
        if source.is_symlink():
            raise ValueError("Report publication does not allow symlinks.")
        try:
            source.resolve(strict=True).relative_to(report_root)
        except (ValueError, FileNotFoundError) as exc:
            raise ValueError("Report path escapes its audit directory.") from exc
    if target_dir.exists():
        raise ValueError("Publication target already exists.")
    target_dir.mkdir(parents=True)
    output_index = target_dir / "index.html"
    shutil.copy2(index_path, output_index)
    html = index_path.read_text(encoding="utf-8")
    rewrites: Dict[str, str] = {}

    for match in LOCAL_REF_RE.finditer(html):
        href = match.group("href")
        if _is_external_or_special(href):
            continue
        decoded_href = unquote(urlsplit(href).path)
        source = (report_dir / decoded_href).resolve()
        if not source.exists() or not source.is_file() or not _inside(source, report_dir):
            raise ValueError("Report assets must remain inside the selected audit directory.")
        relative_asset = source.relative_to(report_root)
        target = target_dir / relative_asset
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for old, new in rewrites.items():
        html = html.replace(f'"{old}"', f'"{new}"')
    output_index.write_text(html, encoding="utf-8")
    return output_index


def package_report_for_vercel(report_dir: Path, static_dir: Path, audit_slug: str = "") -> Path:
    static_dir = static_dir if static_dir.is_absolute() else ROOT_DIR / static_dir
    slug = _safe_slug(audit_slug) if audit_slug else ""
    if not slug:
        _safe_clear_dir(static_dir)
        static_dir.rmdir()
        return _copy_report_with_assets(report_dir, static_dir)

    static_dir.mkdir(parents=True, exist_ok=True)
    current_report_dir = static_dir / "audits" / slug
    if current_report_dir.exists():
        if not _inside(current_report_dir, static_dir):
            raise ValueError("Invalid audit packaging target.")
        shutil.rmtree(current_report_dir)
    return _copy_report_with_assets(report_dir, current_report_dir)


def publish_selected_report(report_dir: Path, *, deployer=None, staging_parent: Path | None = None) -> str:
    """Deploy an isolated immutable report copy and always remove temporary staging."""
    deploy = deployer or deploy_to_vercel
    publication_id = secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="uxui-publication-", dir=staging_parent) as temporary:
        staging_root = Path(temporary)
        report_target = staging_root / "audits" / publication_id
        _copy_report_with_assets(report_dir, report_target)
        url = deploy(
            staging_root,
            production=True,
            public_path=f"audits/{publication_id}",
            prefer_alias=False,
        )
        if not url:
            raise RuntimeError("Publication completed without a public URL.")
        return url


def _vercel_executable() -> str:
    executable = shutil.which("vercel") or shutil.which("vercel.cmd")
    if not executable:
        npm_executable = shutil.which("npm.cmd") or shutil.which("npm")
        if npm_executable:
            completed = subprocess.run(
                [npm_executable, "config", "get", "prefix"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            prefix = (completed.stdout or "").strip()
            candidates = [
                Path(prefix) / "vercel.cmd",
                Path(prefix) / "vercel",
                Path(prefix) / "node_modules" / ".bin" / "vercel.cmd",
                Path(prefix) / "node_modules" / ".bin" / "vercel",
            ] if prefix else []
            for candidate in candidates:
                try:
                    if candidate.exists():
                        return str(candidate)
                except OSError:
                    continue
        raise RuntimeError("Vercel CLI not found. Install it with: npm i -g vercel")
    return executable


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _vercel_subprocess_env() -> Dict[str, str]:
    env = os.environ.copy()
    if os.name != "nt" or "--use-system-ca" in env.get("NODE_OPTIONS", ""):
        return env

    node_executable = shutil.which("node.exe") or shutil.which("node")
    if not node_executable:
        return env
    completed = subprocess.run(
        [node_executable, "-p", "process.versions.node.split('.')[0]"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    try:
        node_major = int((completed.stdout or "").strip())
    except ValueError:
        return env
    if node_major >= 22:
        node_options = env.get("NODE_OPTIONS", "").strip()
        env["NODE_OPTIONS"] = f"{node_options} --use-system-ca".strip()
    return env


def _ensure_vercel_project_link(static_dir: Path) -> None:
    org_id = _env("VERCEL_ORG_ID")
    project_id = _env("VERCEL_PROJECT_ID")
    if not org_id or not project_id:
        return

    vercel_dir = static_dir / ".vercel"
    vercel_dir.mkdir(parents=True, exist_ok=True)
    project_json = vercel_dir / "project.json"
    project_json.write_text(
        json.dumps({"orgId": org_id, "projectId": project_id}, indent=2),
        encoding="utf-8",
    )


def deploy_to_vercel(static_dir: Path, *, production: bool = True, public_path: str = "", prefer_alias: bool = False) -> str:
    executable = _vercel_executable()
    static_dir = static_dir if static_dir.is_absolute() else ROOT_DIR / static_dir
    _ensure_vercel_project_link(static_dir)

    command = [executable, "deploy", ".", "--yes"]
    if production:
        command.append("--prod")
    # Vercel reads VERCEL_TOKEN from the child environment; never expose it in argv.
    vercel_scope = _env("VERCEL_SCOPE")
    if vercel_scope:
        command.extend(["--scope", vercel_scope])
    completed = subprocess.run(
        command,
        cwd=str(static_dir),
        env=_vercel_subprocess_env(),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    )
    output = completed.stdout or ""
    print(output, end="" if output.endswith("\n") else "\n")
    if completed.returncode != 0:
        lowered = output.lower()
        if "login" in lowered or "auth" in lowered or "not authenticated" in lowered:
            raise RuntimeError("Vercel deployment failed because the CLI is not authenticated. Run: vercel login")
        output_tail = "\n".join(output.splitlines()[-12:]).strip()
        detail = f"\n\nVercel output:\n{output_tail}" if output_tail else ""
        raise RuntimeError(f"Vercel deployment failed with exit code {completed.returncode}.{detail}")
    url = _public_deployment_url(output, prefer_alias=prefer_alias)
    if public_path and url:
        return f"{url.rstrip('/')}/{public_path.strip('/')}/"
    return url


def _clean_cli_url(value: str) -> str:
    return value.strip().strip('",.)')


def _public_deployment_url(output: str, *, prefer_alias: bool = False) -> str:
    labeled_candidates: list[tuple[str, str]] = []
    for line in output.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith(("preview:", "production:", "ready:", "deployed to:")):
            labeled_candidates.extend((lowered.split(":", 1)[0], _clean_cli_url(url)) for url in re.findall(r"https://[^\s]+", stripped))
        elif lowered.startswith("aliased:"):
            labeled_candidates.extend(("aliased", _clean_cli_url(url)) for url in re.findall(r"https://[^\s]+", stripped))

    candidates = [url for _label, url in labeled_candidates]
    if not candidates:
        candidates = [_clean_cli_url(url) for url in re.findall(r"https://[^\s]+", output)]

    public_labeled_candidates = [
        (label, url)
        for label, url in labeled_candidates
        if ".vercel.app" in url
        and "api.vercel.com" not in url
        and "vercel.com/" not in url.replace(".vercel.app", "")
    ]
    if prefer_alias:
        for label, url in public_labeled_candidates:
            if label == "aliased":
                return url
    for label, url in public_labeled_candidates:
        if label != "aliased":
            return url

    public_candidates = [
        url
        for url in candidates
        if ".vercel.app" in url
        and "api.vercel.com" not in url
        and "vercel.com/" not in url.replace(".vercel.app", "")
    ]
    if public_candidates:
        return public_candidates[0]

    fallback_candidates = [
        url
        for url in candidates
        if "api.vercel.com" not in url and not url.startswith("https://vercel.com/")
    ]
    return fallback_candidates[-1] if fallback_candidates else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Package and optionally deploy an audit report as a static Vercel site.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_STATIC_DIR))
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--prod", action="store_true", help="Create a production deployment and update the production alias.")
    parser.add_argument("--preview", action="store_true", help="Create a preview deployment instead of production.")
    parser.add_argument("--audit-slug", default="", help="Optional stable slug for a public /audits/<slug>/ report URL.")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    static_dir = Path(args.output_dir)
    audit_slug = _safe_slug(args.audit_slug) if args.audit_slug else ""
    output_index = package_report_for_vercel(report_dir, static_dir, audit_slug=audit_slug)
    print(f"Vercel static report packaged at: {output_index}")

    if args.deploy:
        if args.preview:
            raise RuntimeError("Preview deployment is disabled for isolated Phase 0 publication.")
        url = publish_selected_report(report_dir)
        if not url:
            raise RuntimeError("Vercel deployment completed but no deployment URL was found in CLI output.")
        print(f"Vercel deployment URL: {url}")


if __name__ == "__main__":
    main()
