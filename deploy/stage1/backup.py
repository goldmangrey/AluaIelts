#!/usr/bin/python3
"""Alua-only encrypted local backups. No external destination is configured."""

import fcntl
import hashlib
import json
import os
import resource
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/var/backups/alua/daily")
STATE = Path("/var/lib/alua-backup")
MAX_FILE = 256 * 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024 * 1024
os.umask(0o077)
ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
STATE.mkdir(parents=True, exist_ok=True, mode=0o700)


def run(args, **kwargs):
    return subprocess.run(args, check=True, timeout=600, **kwargs)


def main():
    with (STATE / "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE, MAX_FILE))
        # Recover only our abandoned staging directories after a killed previous run.
        for stale in ROOT.glob(".staging-*"):
            if stale.is_dir() and not stale.is_symlink():
                shutil.rmtree(stale)
        if shutil.disk_usage(ROOT).free < 2 * 1024**3:
            raise RuntimeError("Insufficient free disk reserve")
        if sum(p.stat().st_size for p in ROOT.iterdir() if p.is_file()) > MAX_TOTAL:
            raise RuntimeError(
                "Backup storage budget exceeded; inspect before deleting"
            )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = ROOT / f"alua-{stamp}.dump.age"
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=ROOT) as temp:
            dump = Path(temp) / "alua.dump"
            encrypted = Path(temp) / "alua.dump.age"
            with dump.open("wb") as out:
                run(
                    [
                        "runuser",
                        "-u",
                        "postgres",
                        "--",
                        "pg_dump",
                        "-Fc",
                        "--lock-wait-timeout=10s",
                        "--dbname=alua",
                    ],
                    stdout=out,
                )
            run(["pg_restore", "--list", str(dump)], stdout=subprocess.DEVNULL)
            restore_marker = STATE / "last-restore-success"
            if (
                not restore_marker.exists()
                or time.time() - restore_marker.stat().st_mtime > 7 * 86400
            ):
                run(["/usr/local/libexec/alua-backup-restore-check", str(dump)])
                restore_marker.write_text(stamp + "\n")
            run(
                [
                    "age",
                    "-R",
                    "/etc/alua-backup/recipient",
                    "-o",
                    str(encrypted),
                    str(dump),
                ]
            )
            if not encrypted.stat().st_size:
                raise RuntimeError("Empty encrypted backup")
            checksum = hashlib.sha256(encrypted.read_bytes()).hexdigest()
            encrypted.rename(target)
        # Rotation only of this job's successful archives, after a new successful backup.
        archives = sorted(ROOT.glob("alua-*.dump.age"), reverse=True)
        for old in archives[14:]:
            old.unlink()
        status = {
            "last_success_utc": stamp,
            "file": target.name,
            "bytes": target.stat().st_size,
            "sha256": checksum,
            "external_backup": "BLOCKED: no configured destination",
        }
        tmp = STATE / "status.next"
        tmp.write_text(json.dumps(status, indent=2) + "\n")
        tmp.replace(STATE / "status.json")
        (STATE / "failure").unlink(missing_ok=True)
        print(
            "Alua encrypted LOCAL backup succeeded; external backup BLOCKED", flush=True
        )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError):
        (STATE / "failure").write_text(datetime.now(timezone.utc).isoformat() + "\n")
        # No command arguments, database credentials, SQL or private keys in the error log.
        print(
            "Alua backup FAILED; inspect service and /var/lib/alua-backup/failure",
            flush=True,
        )
        raise SystemExit(1)
