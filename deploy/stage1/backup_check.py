#!/usr/bin/python3
import json
from datetime import datetime, timezone
from pathlib import Path

state = Path("/var/lib/alua-backup")
try:
    status = json.loads((state / "status.json").read_text())
    last = datetime.strptime(status["last_success_utc"], "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )
    archive = Path("/var/backups/alua/daily") / status["file"]
    assert (datetime.now(timezone.utc) - last).total_seconds() < 30 * 3600
    assert archive.is_file() and archive.stat().st_size == status["bytes"]
    assert not (state / "failure").exists()
    restore = state / "last-restore-success"
    assert restore.exists()
    assert datetime.now(timezone.utc).timestamp() - restore.stat().st_mtime < 9 * 86400
except (OSError, ValueError, KeyError, AssertionError):
    print("ALUA BACKUP ALERT: missing, failed or older than 30 hours", flush=True)
    raise SystemExit(1)
print("Alua local backup fresh; external backup BLOCKED", flush=True)
