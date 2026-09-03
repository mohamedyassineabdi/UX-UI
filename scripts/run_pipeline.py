import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.audit.workspace import AuditWorkspace

NAVIGATOR_DIR = ROOT_DIR / "navigator"
DEFAULT_TEMPLATE_CANDIDATE = ROOT_DIR / "shared" / "config" / "UX-Audit-Workbook-template.xlsx"

load_dotenv(ROOT_DIR / ".env")


def run_command(args, cwd: Optional[Path] = None, timeout_sec: Optional[int] = None) -> None:
    try:
        completed = subprocess.run(
            [str(arg) for arg in args],
            cwd=str(cwd) if cwd else None,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{args[0]} timed out after {timeout_sec}s") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"{args[0]} exited with code {completed.returncode}")


def run_command_capture(args, cwd: Optional[Path] = None) -> str:
    completed = subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = completed.stdout or ""
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    if completed.returncode != 0:
        raise RuntimeError(f"{args[0]} exited with code {completed.returncode}")
    return output


def ensure_dir(dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)


def ensure_file_exists(file_path: Path) -> None:
    if not file_path.exists():
        raise RuntimeError(f"Expected file was not created: {file_path}")


def env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def read_json_file(file_path: Path):
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_crawler_output(file_path: Path):
    data = read_json_file(file_path)

    if isinstance(data, dict):
        crawler_error = str(data.get("error") or "").strip()
        if crawler_error:
            raise RuntimeError(f"Crawler failed for this website: {crawler_error}")

    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full UX/UI auditor pipeline.")
    parser.add_argument("url", help="Website URL to crawl and audit")
    parser.add_argument(
        "--job-id",
        default="",
        help="Trusted server audit job identifier. Manual runs receive a unique identifier when omitted.",
    )
    parser.add_argument(
        "--mode",
        choices=("detailed", "gtm"),
        default="detailed",
        help="Audit mode. 'detailed' runs the existing sheet-based audit. 'gtm' runs the go-to-market audit.",
    )
    parser.add_argument(
        "--workbook-template",
        default="",
        help="Optional workbook template path. If omitted, the pipeline auto-discovers one.",
    )
    parser.add_argument(
        "--skip-workbook",
        action="store_true",
        help="Generate checks JSON but skip workbook export",
    )
    parser.add_argument(
        "--skip-vision",
        action="store_true",
        help="When --mode gtm is used, skip the multimodal vision synthesis layer.",
    )
    parser.add_argument(
        "--deploy-vercel",
        action="store_true",
        help="When --mode gtm is used, package and deploy the generated GTM report to Vercel.",
    )
    parser.add_argument(
        "--vercel-preview",
        action="store_true",
        help="Create a Vercel preview deployment instead of a production deployment.",
    )
    parser.add_argument(
        "--vercel-prod",
        action="store_true",
        help="Create a production Vercel deployment and update the production alias.",
    )
    return parser.parse_args()


def resolve_workbook_template(explicit_path: str) -> Path:
    candidates = []

    if explicit_path:
        candidates.append(Path(explicit_path))

    env_path = os.getenv("AUDIT_WORKBOOK_TEMPLATE", "").strip()
    if env_path:
        candidates.append(Path(env_path))

    candidates.append(DEFAULT_TEMPLATE_CANDIDATE)

    for candidate in candidates:
        resolved = candidate if candidate.is_absolute() else ROOT_DIR / candidate
        if resolved.exists():
            return resolved

    raise FileNotFoundError(
        "Detailed audits require AUDIT_WORKBOOK_TEMPLATE or shared/config/UX-Audit-Workbook-template.xlsx."
    )


def run_pipeline(args: argparse.Namespace) -> None:
    job_id = args.job_id or f"manual-{uuid.uuid4().hex}"
    workspace = AuditWorkspace.for_repository(job_id, ROOT_DIR)
    workspace.prepare(mode=args.mode)
    checks_output = workspace.checks
    workbook_output = workspace.workbook
    report_output_dir = workspace.report
    gtm_output = workspace.gtm_audit
    vercel_output_dir = workspace.publication
    website_menu = workspace.website_menu
    html_cleaned = workspace.html_cleaned
    rendered_ui = workspace.rendered_ui
    audit_results = workspace.audit_results

    print(f"Audit job ID: {workspace.job_id}")
    print(f"Audit workspace: {workspace.root}")

    print("\n[1/5] Running crawler...\n")
    crawler_args = [
        sys.executable,
        NAVIGATOR_DIR / "crawler.py",
        args.url,
        "--json-out",
        website_menu,
        "--timeout",
        env_int("WEBSITE_CRAWLER_PAGE_TIMEOUT_SEC", 12),
    ]
    crawler_args.extend(["--locale", os.getenv("UX_AUDIT_LOCALE", "auto"), "--robots-policy", os.getenv("UX_AUDIT_ROBOTS_POLICY", "respect")])
    if env_flag("UX_AUDIT_INCLUDE_AUTH_PAGES", False):
        crawler_args.append("--include-auth-pages")
    if env_flag("CRAWLER_USE_AI_NAV") or env_flag("USE_AI_NAV"):
        crawler_args.append("--use-ai-nav")

    run_command(
        crawler_args,
        cwd=ROOT_DIR,
        timeout_sec=max(60, env_int("WEBSITE_CRAWLER_TIMEOUT_SEC", 240)),
    )

    ensure_file_exists(website_menu)
    validate_crawler_output(website_menu)

    print("\n[2/5] Running page audit...\n")
    run_command([sys.executable, "-m", "src.main", "--job-id", workspace.job_id], cwd=ROOT_DIR)

    ensure_file_exists(html_cleaned)
    ensure_file_exists(rendered_ui)
    ensure_file_exists(audit_results)

    print("\n[3/5] Generating checks JSON...\n")
    checks_args = [
        sys.executable,
        "-m",
        "src.audit.checks.run_sheet_checks",
        "--cleaned",
        html_cleaned,
        "--rendered",
        rendered_ui,
        "--output",
        checks_output,
    ]
    checks_args.extend(["--results", audit_results])
    run_command(checks_args, cwd=ROOT_DIR)

    ensure_file_exists(checks_output)

    workbook_for_report = ""
    if args.mode == "detailed":
        if args.skip_workbook:
            print("\n[4/5] Workbook export skipped.\n")
        else:
            workbook_template = resolve_workbook_template(args.workbook_template)

            print("\n[4/5] Exporting workbook...\n")
            print(f"Using workbook template: {workbook_template}")
            run_command(
                [
                    sys.executable,
                    "-m",
                    "src.audit.export.write_checks_to_workbook",
                    "--template",
                    workbook_template,
                    "--checks",
                    checks_output,
                    "--output",
                    workbook_output,
                ],
                cwd=ROOT_DIR,
            )

            ensure_file_exists(workbook_output)
            workbook_for_report = str(workbook_output)

        print("\n[5/5] Generating audit report site...\n")
        report_args = [
            sys.executable,
            "-m",
            "src.report.generate_audit_report",
            "--website-menu",
            website_menu,
            "--cleaned",
            html_cleaned,
            "--rendered",
            rendered_ui,
            "--checks",
            checks_output,
            "--output-dir",
            report_output_dir,
        ]
        if workbook_for_report:
            report_args.extend(["--workbook", workbook_for_report])
        report_args.extend(["--results", audit_results])
        run_command(report_args, cwd=ROOT_DIR)
        ensure_file_exists(report_output_dir / "index.html")
    else:
        print("\n[4/5] Generating GTM audit...\n")
        gtm_args = [
            sys.executable,
            "-m",
            "src.gtm_audit.generate_gtm_audit",
            "--website-menu",
            website_menu,
            "--cleaned",
            html_cleaned,
            "--rendered",
            rendered_ui,
            "--checks",
            checks_output,
            "--output",
            gtm_output,
        ]
        gtm_args.extend(["--results", audit_results])
        gtm_args.extend(["--coverage", workspace.coverage_manifest])
        if args.skip_vision:
            gtm_args.append("--skip-vision")
        run_command(gtm_args, cwd=ROOT_DIR)
        ensure_file_exists(gtm_output)

        print("\n[5/5] Generating GTM report site...\n")
        run_command(
            [
                sys.executable,
                "-m",
                "src.gtm_audit.generate_gtm_report",
                "--input",
                gtm_output,
                "--output-dir",
                report_output_dir,
            ],
            cwd=ROOT_DIR,
        )
        ensure_file_exists(report_output_dir / "index.html")

        disable_vercel_deploy = os.getenv("GTM_DISABLE_VERCEL_DEPLOY", "").strip().lower() in {"1", "true", "yes", "on"}
        # Publication must be an explicit operator action. Environment state must never
        # make an authenticated audit public before review.
        deploy_vercel = not disable_vercel_deploy and args.deploy_vercel
        print("\n[6/6] Packaging GTM report for Vercel...\n")
        deploy_args = [
            sys.executable,
            "-m",
            "src.gtm_audit.vercel_static_deploy",
            "--report-dir",
            report_output_dir,
            "--output-dir",
            vercel_output_dir,
        ]
        if deploy_vercel:
            deploy_args.append("--deploy")
            deploy_args.extend(["--audit-slug", f"website-{datetime.now().strftime('%Y%m%d%H%M%S')}"])
            if args.vercel_preview:
                deploy_args.append("--preview")
            elif args.vercel_prod:
                deploy_args.append("--prod")
        try:
            deploy_output = run_command_capture(deploy_args, cwd=ROOT_DIR)
        except RuntimeError as error:
            if not deploy_vercel:
                raise
            deploy_output = ""
            print(
                "\nVercel deployment failed, but the audit report was generated and packaged locally.",
                file=sys.stderr,
            )
            print(str(error), file=sys.stderr)

        deployment_urls = re.findall(r"https://[^\s]+", deploy_output)
        if deployment_urls:
            print(f"Final Vercel link: {deployment_urls[-1]}")
        if not deployment_urls:
            print(f"Vercel static package: {vercel_output_dir / 'index.html'}")

    print("\nPipeline completed successfully.")
    print(f"Navigation JSON: {website_menu}")
    print(f"Cleaned HTML JSON: {html_cleaned}")
    print(f"Rendered UI JSON: {rendered_ui}")
    print(f"Checks JSON: {checks_output}")
    if workbook_for_report:
        print(f"Workbook: {workbook_output}")
    if args.mode == "gtm":
        print(f"GTM audit JSON: {gtm_output}")
        print(f"Vercel static package: {vercel_output_dir / 'index.html'}")
    print(f"Audit report: {report_output_dir / 'index.html'}")


if __name__ == "__main__":
    try:
        run_pipeline(parse_args())
    except Exception as error:
        print("\nPipeline failed:", file=sys.stderr)
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
