#!/usr/bin/env python3
"""Career OS operational CLI — migrations, backup, restore, and health checks."""

from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings, resolve_paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_MIGRATION_HEAD = "015_user_plan_tier"
DEFAULT_API_URL = "http://127.0.0.1:8000"
DEFAULT_LOGIN = ("user@example.com", "careeros-dev-password")

RESUME_LABEL_ALIASES = {
    "ai": "AI Resume",
    "it": "IT Resume",
    "general": "General Resume",
    "construction": "Construction Resume",
    "production": "Production Resume",
}


def _settings() -> Settings:
    return resolve_paths(get_settings(), PROJECT_ROOT)


def cmd_version(_: argparse.Namespace) -> int:
    settings = _settings()
    print(f"Career OS {settings.app_version} ({settings.environment})")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    target = args.revision or "head"
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", target], cwd=backend_dir, check=True)
    print(f"Migrations applied: {target}")
    return 0


def cmd_migrate_check(_: argparse.Namespace) -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    if EXPECTED_MIGRATION_HEAD not in result.stdout:
        print(f"Expected migration head {EXPECTED_MIGRATION_HEAD} not found:\n{result.stdout}")
        return 1
    print(f"Migration head OK: {EXPECTED_MIGRATION_HEAD}")
    return 0


def _backup_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = base / f"career-os-backup-{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def cmd_backup(args: argparse.Namespace) -> int:
    settings = _settings()
    output_root = Path(args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    backup_path = _backup_dir(output_root)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "app_version": settings.app_version,
        "migration_head": EXPECTED_MIGRATION_HEAD,
        "database_url_redacted": settings.database_url.split("@")[-1],
    }

    if settings.storage_path.exists():
        shutil.copytree(settings.storage_path, backup_path / "storage")
    if settings.prompts_path.exists():
        shutil.copytree(settings.prompts_path, backup_path / "prompts")

    db_url = settings.database_url
    if db_url.startswith("postgresql"):
        dump_file = backup_path / "database.sql"
        subprocess.run(
            ["pg_dump", db_url, "-f", str(dump_file)],
            check=True,
        )
        manifest["database_dump"] = dump_file.name
    else:
        manifest["database_dump"] = None
        print("Warning: DATABASE_URL is not PostgreSQL; skipping pg_dump.")

    (backup_path / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    archive = output_root / f"{backup_path.name}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(backup_path, arcname=backup_path.name)

    shutil.rmtree(backup_path)
    print(f"Backup created: {archive}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    settings = _settings()
    source = Path(args.input).resolve()
    if not source.exists():
        print(f"Backup not found: {source}", file=sys.stderr)
        return 1

    work_dir = source.parent / ".restore-work"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir()

    if source.suffix == ".gz" or source.name.endswith(".tar.gz"):
        with tarfile.open(source, "r:gz") as tar:
            tar.extractall(work_dir)
        entries = [p for p in work_dir.iterdir() if p.is_dir()]
        if len(entries) != 1:
            print("Invalid backup archive structure", file=sys.stderr)
            return 1
        backup_path = entries[0]
    else:
        backup_path = source

    manifest_path = backup_path / "manifest.json"
    if manifest_path.exists():
        print(manifest_path.read_text(encoding="utf-8"))

    if args.yes and (backup_path / "storage").exists():
        if settings.storage_path.exists():
            shutil.rmtree(settings.storage_path)
        shutil.copytree(backup_path / "storage", settings.storage_path)

    dump_file = backup_path / "database.sql"
    if args.yes and dump_file.exists() and settings.database_url.startswith("postgresql"):
        subprocess.run(["psql", settings.database_url, "-f", str(dump_file)], check=True)

    shutil.rmtree(work_dir, ignore_errors=True)
    print("Restore completed. Restart the API if it is running.")
    return 0


def _api_get(base: str, path: str, token: str | None = None, timeout: int = 5) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{base.rstrip('/')}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _api_post_json(base: str, path: str, payload: dict, token: str | None = None, timeout: int = 10) -> tuple[int, dict]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base.rstrip('/')}{path}", data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(detail)
        except json.JSONDecodeError:
            return exc.code, {"detail": detail}


def _login(base: str, email: str, password: str) -> str:
    status, data = _api_post_json(base, "/api/v1/auth/login", {"email": email, "password": password})
    if status != 200:
        raise RuntimeError(f"Login failed ({status}): {data.get('detail', data)}")
    return data["access_token"]


def _resolve_resume_label(label: str) -> str:
    key = label.strip().lower()
    if key in RESUME_LABEL_ALIASES:
        return RESUME_LABEL_ALIASES[key]
    return label.strip()


def _upload_resume(base: str, token: str, file_path: Path, label: str) -> tuple[int, dict]:
    boundary = uuid.uuid4().hex
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()

    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="label"\r\n\r\n',
            f"{label}\r\n".encode("utf-8"),
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            ).encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    request = urllib.request.Request(
        f"{base.rstrip('/')}/api/v1/resumes/master", data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(detail)
        except json.JSONDecodeError:
            return exc.code, {"detail": detail}


def cmd_doctor(args: argparse.Namespace) -> int:
    base = args.url.rstrip("/")
    settings = _settings()
    print("Career OS — system check")
    print("=" * 40)

    ok = True
    for path, label in (("/api/v1/health", "API"), ("/api/v1/ready", "Database")):
        try:
            status, data = _api_get(base, path, timeout=args.timeout)
            detail = data.get("status", data)
            print(f"  {label + ':':14} OK ({detail})")
        except urllib.error.URLError as exc:
            print(f"  {label + ':':14} FAILED — {exc}")
            ok = False

    print(f"  {'AI enabled:':14} {'yes' if settings.ai_enabled else 'no'}")
    print(f"  {'OpenAI key:':14} {'set' if settings.openai_api_key else 'missing'}")
    print(f"  {'Anthropic key:':14} {'set' if settings.anthropic_api_key else 'missing'}")
    if not settings.openai_api_key or not settings.anthropic_api_key:
        ok = False

    email, password = args.email, args.password
    try:
        token = _login(base, email, password)
        _, me = _api_get(base, "/api/v1/auth/me", token=token, timeout=args.timeout)
        print(f"  {'Account:':14} {me.get('email', 'unknown')}")
        _, resumes = _api_get(base, "/api/v1/resumes/master", token=token, timeout=args.timeout)
        count = len(resumes) if isinstance(resumes, list) else 0
        print(f"  {'Resumes:':14} {count} uploaded")
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"  {'Account:':14} FAILED — {exc}")
        ok = False

    print()
    if ok:
        print("All checks passed.")
        inbox = PROJECT_ROOT / "inbox"
        print(f"Drop your resume PDF in: {inbox}")
        print('Then run: career-os upload-resume --file inbox/your-resume.pdf --type ai')
    else:
        print("Some checks failed. Fix the items above and run: career-os doctor")
        return 1
    return 0


def cmd_upload_resume(args: argparse.Namespace) -> int:
    base = args.url.rstrip("/")
    file_path = Path(args.file).resolve()
    if not file_path.is_file():
        print(f"File not found: {file_path}", file=sys.stderr)
        return 1

    label = _resolve_resume_label(args.type if args.label is None else args.label)
    token = _login(base, args.email, args.password)
    status, data = _upload_resume(base, token, file_path, label)
    if status in (200, 201):
        print(f"Resume uploaded: {data.get('original_filename', file_path.name)}")
        print(f"  Label: {data.get('label', label)}")
        print(f"  ID:    {data.get('id')}")
        return 0
    print(f"Upload failed ({status}): {data.get('detail', data)}", file=sys.stderr)
    print("Valid types: ai, it, general, construction, production", file=sys.stderr)
    return 1


def cmd_health(args: argparse.Namespace) -> int:
    base = args.url.rstrip("/")
    for path in ("/api/v1/health", "/api/v1/ready"):
        url = f"{base}{path}"
        try:
            with urllib.request.urlopen(url, timeout=args.timeout) as response:
                body = response.read().decode("utf-8")
                print(f"{path}: {response.status} {body}")
        except urllib.error.URLError as exc:
            print(f"{path}: FAILED ({exc})", file=sys.stderr)
            return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="career-os", description="Career OS operations CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    version_parser = sub.add_parser("version", help="Print application version")
    version_parser.set_defaults(func=cmd_version)

    migrate_parser = sub.add_parser("migrate", help="Run Alembic migrations")
    migrate_parser.add_argument("--revision", default="head", help="Alembic revision (default: head)")
    migrate_parser.set_defaults(func=cmd_migrate)

    check_parser = sub.add_parser("migrate-check", help="Verify expected migration head")
    check_parser.set_defaults(func=cmd_migrate_check)

    backup_parser = sub.add_parser("backup", help="Backup database and storage")
    backup_parser.add_argument("--output", default="backups", help="Output directory")
    backup_parser.set_defaults(func=cmd_backup)

    restore_parser = sub.add_parser("restore", help="Restore from backup archive")
    restore_parser.add_argument("--input", required=True, help="Path to .tar.gz backup")
    restore_parser.add_argument("--yes", action="store_true", help="Apply restore without prompt")
    restore_parser.set_defaults(func=cmd_restore)

    health_parser = sub.add_parser("health", help="Check API health endpoints")
    health_parser.add_argument("--url", default=DEFAULT_API_URL, help="API base URL")
    health_parser.add_argument("--timeout", type=int, default=5, help="Request timeout seconds")
    health_parser.set_defaults(func=cmd_health)

    doctor_parser = sub.add_parser("doctor", help="Friendly system check (no Swagger needed)")
    doctor_parser.add_argument("--url", default=DEFAULT_API_URL, help="API base URL")
    doctor_parser.add_argument("--email", default=DEFAULT_LOGIN[0])
    doctor_parser.add_argument("--password", default=DEFAULT_LOGIN[1])
    doctor_parser.add_argument("--timeout", type=int, default=5)
    doctor_parser.set_defaults(func=cmd_doctor)

    upload_parser = sub.add_parser("upload-resume", help="Upload a resume PDF/DOCX")
    upload_parser.add_argument("--file", required=True, help="Path to resume file")
    upload_parser.add_argument(
        "--type",
        choices=sorted(RESUME_LABEL_ALIASES.keys()),
        default="ai",
        help="Resume category (default: ai)",
    )
    upload_parser.add_argument("--label", default=None, help="Exact label override (advanced)")
    upload_parser.add_argument("--url", default=DEFAULT_API_URL)
    upload_parser.add_argument("--email", default=DEFAULT_LOGIN[0])
    upload_parser.add_argument("--password", default=DEFAULT_LOGIN[1])
    upload_parser.set_defaults(func=cmd_upload_resume)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
