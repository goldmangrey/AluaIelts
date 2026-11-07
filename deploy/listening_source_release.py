"""Alua release-copy/drop-in workflow. No migrations or environment edits."""

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from urllib.request import urlopen

meta_path = Path(sys.argv[sys.argv.index("--meta") + 1])
meta = json.loads(meta_path.read_text())
old = Path("/opt/alua/releases") / meta["previous_backend"]
new = old.parent / meta["candidate_backend_id"]
assert old.name.startswith(
    ("submit-hotfix-", "source-fidelity-")
) and new.name.startswith("source-fidelity-")
assert (
    old.parent == new.parent
    and "/" not in meta["previous_backend"]
    and "/" not in meta["candidate_backend_id"]
)
allowed = ("app/content/listening_v1/",)
assert all(
    (
        name
        in {
            "app/modules/listening/catalog.py",
            "app/modules/listening/source_materials.py",
        }
        or name.startswith(allowed)
    )
    and ".." not in Path(name).parts
    and not name.startswith("app/content/listening_v1/keys/")
    for name in meta["backend_files"]
)
backup = Path("/var/backups/alua") / ("pre-" + new.name)
drop = Path(
    "/etc/systemd/system/alua-api.service.d/zzzzzzzzzzzzz-source-fidelity-20261107.conf"
)


def active():
    return subprocess.check_output(
        ["systemctl", "show", "alua-api", "--value", "-p", "WorkingDirectory"],
        text=True,
    ).strip()


def runtime_env():
    pid = subprocess.check_output(
        ["systemctl", "show", "alua-api", "--value", "-p", "MainPID"], text=True
    ).strip()
    env = dict(os.environ)
    for pair in Path("/proc/" + pid + "/environ").read_bytes().split(b"\0"):
        if b"=" in pair:
            k, v = pair.split(b"=", 1)
            env[k.decode()] = v.decode()
    return env


DB_CHECK = """import json
from sqlalchemy import text
from app.db.database import get_database
result={}
with get_database().engine.connect() as c:
 c.execute(text('SET TRANSACTION READ ONLY'))
 for table in ['listening_attempts','listening_mutations','reading_attempts','reading_mutations','firebase_identities']:
  n,h=c.execute(text("SELECT count(*), md5(coalesce(string_agg(h, ',' ORDER BY h), '')) FROM (SELECT md5(row_to_json(t)::text) h FROM public."+table+" t) s")).one();result[table]={'count':n,'digest':h}
print(json.dumps(result))"""


def run(code, cwd):
    result = subprocess.run(
        [
            "runuser",
            "-u",
            "alua",
            "--preserve-environment",
            "--",
            str(cwd / ".venv/bin/python"),
            "-B",
            "-c",
            code,
        ],
        cwd=cwd,
        env=runtime_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        names = [
            line.split(":", 1)[0]
            for line in result.stderr.splitlines()
            if "Error:" in line
        ]
        print(json.dumps({"check_error_types": names[-3:]}))
        raise RuntimeError("Candidate/runtime check failed; no credentials logged")
    return json.loads(result.stdout.strip().splitlines()[-1])


def healthy():
    for _ in range(30):
        try:
            with urlopen("http://127.0.0.1:8010/api/v1/health", timeout=2) as r:
                if json.load(r)["status"] == "ok":
                    return
        except (OSError, ValueError):
            time.sleep(0.5)
            continue
        time.sleep(0.5)
    raise RuntimeError("Health check failed")


def restart():
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "restart", "alua-api"], check=True)
    healthy()


if "--rollback" in sys.argv:
    assert active() == str(new) and old.is_dir() and drop.exists()
    drop.rename(drop.with_suffix(".disabled"))
    restart()
    assert active() == str(old)
    print(json.dumps({"rollback": "COMPLETED", "release": str(old)}))
    sys.exit()
if "--activate" in sys.argv:
    assert (
        active() == str(old)
        and new.is_dir()
        and (backup / "stage.json").exists()
        and not drop.exists()
    )
    (backup / "data-before-activation.json").write_text(
        json.dumps(run(DB_CHECK, old), indent=2)
    )
    if Path(__file__).resolve() != (backup / "release.py").resolve():
        shutil.copy2(__file__, backup / "release.py")
    drop.write_text(
        "[Service]\nWorkingDirectory="
        + str(new)
        + "\nExecStart=\nExecStart="
        + str(new)
        + "/.venv/bin/python -B -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --proxy-headers --forwarded-allow-ips=127.0.0.1 --no-access-log\n"
    )
    try:
        restart()
        assert active() == str(new)
        with urlopen("http://127.0.0.1:8010/openapi.json", timeout=10) as r:
            d = json.load(r)
        for name, fields in [
            ("Submit", ["answers", "state", "answers_checksum", "local_revision"]),
            ("SubmitMutation", ["answers", "answers_checksum", "local_revision"]),
        ]:
            assert set(fields) <= set(d["components"]["schemas"][name]["properties"])
    except Exception:  # noqa: BLE001 - restore the old service on any activation failure
        drop.rename(drop.with_suffix(".disabled"))
        restart()
        raise RuntimeError("Activation failed; prior backend restored")
    after = run(DB_CHECK, new)
    (backup / "data-after.json").write_text(json.dumps(after, indent=2))
    before = json.loads((backup / "data-before-activation.json").read_text())
    print(
        json.dumps(
            {
                "backend_release": str(new),
                "previous_release": str(old),
                "health": "PASS",
                "contract": "PASS",
                "data_fingerprints_unchanged": before == after,
                "backup": str(backup),
                "drop_in": str(drop),
            }
        )
    )
    sys.exit()
assert (
    active() == str(old) and not new.exists() and not (backup / "stage.json").exists()
)
assert (old / ".venv/bin/python").is_file()
payload = Path(meta["archive"])
assert hashlib.sha256(payload.read_bytes()).hexdigest() == meta["archive_sha256"]
backup.mkdir(mode=0o700, exist_ok=True)
(backup / "data-before.json").write_text(json.dumps(run(DB_CHECK, old), indent=2))
with tarfile.open(backup / "backend-before.tar.gz", "w:gz") as t:
    t.add(old, arcname=old.name)
shutil.copytree(old, new, symlinks=True)
with tarfile.open(payload) as t:
    assert set(t.getnames()) == set(meta["backend_files"])
    assert all(m.isfile() for m in t.getmembers())
    assert all(
        (new / name).resolve().is_relative_to(new.resolve())
        for name in meta["backend_files"]
    )
    t.extractall(new, filter="data")
# copytree preserves modes but not owners: retain private catalog access.
for source in [old, *old.rglob("*")]:
    target = new if source == old else new / source.relative_to(old)
    st = source.lstat()
    os.chown(target, st.st_uid, st.st_gid, follow_symlinks=False)
for name, h in meta["backend_files"].items():
    data = (new / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == h
    prior = old / name
    st = (
        prior.stat()
        if prior.exists()
        else (old / "app/modules/listening/catalog.py").stat()
    )
    os.chown(new / name, st.st_uid, st.st_gid)
    os.chmod(new / name, st.st_mode & 0o777 if prior.exists() else 0o644)
    if name.endswith(".py"):
        ast.parse(data)
    elif name.endswith(".json"):
        json.loads(data)
    elif name.endswith(".png"):
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
for p in old.rglob("*"):
    if (
        p.is_file()
        and not p.is_symlink()
        and str(p.relative_to(old)) not in meta["backend_files"]
    ):
        assert (
            hashlib.sha256(p.read_bytes()).digest()
            == hashlib.sha256((new / p.relative_to(old)).read_bytes()).digest()
        )
# Persistent permission gate: every copied Reading file retains owner/group/mode.
for source in (old / "app/content/reading_v1").rglob("*"):
    target = new / source.relative_to(old)
    a = source.lstat()
    b = target.lstat()
    assert (a.st_uid, a.st_gid, a.st_mode) == (b.st_uid, b.st_gid, b.st_mode)
run(
    """import json
from app.modules.reading.catalog import ReadingCatalog
from app.modules.listening.catalog import ListeningCatalog
r=ReadingCatalog();l=ListeningCatalog()
assert len(r.exams)==72 and len(l.exams)==72
for exam in l.exams.values():
 for part in exam['parts']:
  for material in part.get('visual_materials',[]):l.asset(exam,material['asset_id'])
print(json.dumps({'reading_catalog_access':'PASS','listening_catalog_access':'PASS'}))""",
    new,
)
contract = run(
    """import json
from app.main import app
d=app.openapi()['components']['schemas']
assert {'answers','state','answers_checksum','local_revision'}<=set(d['Submit']['properties'])
assert {'answers','answers_checksum','local_revision'}<=set(d['SubmitMutation']['properties'])
print(json.dumps({'contract':'PASS'}))""",
    new,
)
# Additive, immutable publication also keeps attempts created during this release
# readable after a code rollback. Old catalog/manifest/code remain untouched.
for name, hashed in meta["backend_files"].items():
    if not name.startswith("app/content/listening_v1/assets/public/"):
        continue
    target = old / name
    if target.exists():
        assert hashlib.sha256(target.read_bytes()).hexdigest() == hashed
        continue
    shutil.copy2(new / name, target)
    st = (new / name).stat()
    os.chown(target, st.st_uid, st.st_gid)
shutil.copy2(__file__, backup / "release.py")
shutil.copy2(meta_path, backup / "release-meta.json")
(backup / "rollback.json").write_text(
    json.dumps(
        {
            "old_release": str(old),
            "new_release": str(new),
            "drop_in": str(drop),
            "worker_before": meta["worker_previous"],
        },
        indent=2,
    )
)
(backup / "stage.json").write_text(
    json.dumps(
        {
            "candidate": str(new),
            "contract": contract,
            "unchanged_non_payload_files": True,
            "backup_archive_sha256": hashlib.sha256(
                (backup / "backend-before.tar.gz").read_bytes()
            ).hexdigest(),
        },
        indent=2,
    )
)
print(
    json.dumps(
        {
            "staged": str(new),
            "backup": str(backup),
            "runtime_contract": "PASS",
            "non_payload_files": "UNCHANGED",
            "rollback": "READY",
        }
    )
)
