"""Narrow Reading release-copy deployment. No DB, migrations or environment writes."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path
from urllib.request import urlopen

p = argparse.ArgumentParser()
p.add_argument("--meta", type=Path, required=True)
p.add_argument("action", choices=["stage", "activate", "rollback"])
a = p.parse_args()
m = json.loads(a.meta.read_text())
root = Path("/opt/alua/releases")
old = root / m["previous_backend"]
new = root / m["candidate_backend_id"]
rescue = root / (m["candidate_backend_id"] + "-rollback")
backup = Path("/var/backups/alua") / ("pre-" + new.name)
assert old.parent == new.parent == root and new.name.startswith("reading-hotfix-")
allowed = {
    "app/modules/reading/catalog.py",
    "app/content/reading_v1/manifest.json",
    "app/content/reading_v1/corrections.jsonl",
}
allowed.update(
    "app/content/reading_v1/" + x
    for x in [
        "exams/cambridge_06/test_01.json",
        "exams/cambridge_07/test_01.json",
        "exams/cambridge_07/test_04.json",
        "exams/cambridge_14/test_02.json",
        "exams/cambridge_16/test_02.json",
        "exams/cambridge_16/test_03.json",
        "assets/cambridge_07/cambridge-07-test-01-p-2-g-14-20-pdf-026-diagram-fidelity-v1.png",
    ]
)
allowed.update(
    "scripts/reading_dataset/" + x
    for x in [
        "engine.py",
        "enrich.py",
        "pdf_support.py",
        "source_reviews.json",
        "validator.py",
        "confirmed_hotfixes.py",
        "confirmed_hotfixes.json",
        "apply_confirmed_hotfix.py",
    ]
)
assert set(m["backend_files"]) == allowed
assert all(not Path(x).is_absolute() and ".." not in Path(x).parts for x in allowed)
drop = Path(
    "/etc/systemd/system/alua-api.service.d/zzzzzzzzzzzzzz-reading-hotfix-20261108.conf"
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def active():
    return subprocess.check_output(
        ["systemctl", "show", "alua-api", "--value", "-p", "WorkingDirectory"],
        text=True,
    ).strip()


def probe(folder):
    code = (
        "import json;from app.modules.reading.catalog import ReadingCatalog;c=ReadingCatalog();assert len(c.exams)==72;assert all(c.entries[e]['enabled_for_private_practice'] for e in "
        + repr(m["exam_ids"])
        + ");print(json.dumps({'reading_catalog':'PASS','assets':len(c.assets)}))"
    )
    r = subprocess.run(
        [
            "runuser",
            "-u",
            "alua",
            "--",
            str(folder / ".venv/bin/python"),
            "-B",
            "-c",
            code,
        ],
        cwd=folder,
        check=False,
        capture_output=True,
        text=True,
    )
    if r.returncode:
        raise RuntimeError(
            "Service-user catalog preflight failed; private diagnostics withheld"
        )
    return json.loads(r.stdout)


def activate(folder):
    drop.write_text(
        "[Service]\nWorkingDirectory="
        + str(folder)
        + "\nExecStart=\nExecStart="
        + str(folder)
        + "/.venv/bin/python -B -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --proxy-headers --forwarded-allow-ips=127.0.0.1 --no-access-log\n"
    )
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "restart", "alua-api"], check=True)
    for _ in range(30):
        try:
            with urlopen("http://127.0.0.1:8010/api/v1/health", timeout=2) as r:
                if json.load(r)["status"] == "ok":
                    assert active() == str(folder)
                    return
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    raise RuntimeError("Health failed")


def owner_write(path, data, owner, mode=0o640):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chown(path, owner.st_uid, owner.st_gid)
    os.chmod(path, mode)
    # Newly introduced directories must also be traversable by the service user.
    for parent in path.parents:
        if parent in [new, rescue, root]:
            break
        if parent.stat().st_uid == 0:
            os.chown(parent, owner.st_uid, owner.st_gid)


def revision(manifest):
    payload = {
        "sources": manifest["sources"],
        "exams": manifest["exams"],
        "generator": manifest["generator_sha256"],
        "schemas": manifest["schema_sha256"],
        "retained_assets": manifest["retained_assets"],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


if a.action == "stage":
    assert (
        active() == str(old)
        and not new.exists()
        and not rescue.exists()
        and not drop.exists()
    )
    for name, h in {**m["expected_before"], **m["keys"]}.items():
        f = old / name
        assert (sha(f) if f.exists() else None) == h, name
    assert sha(Path(m["archive"])) == m["archive_sha256"]
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    with tarfile.open(backup / "backend-before.tar.gz", "w:gz") as t:
        for name in sorted(allowed):
            if (old / name).exists():
                t.add(old / name, arcname=name, recursive=False)
    subprocess.run(["cp", "-a", str(old), str(new)], check=True)
    owner = (old / "app").stat()
    with tarfile.open(m["archive"]) as t:
        assert {i.name for i in t.getmembers()} == allowed
        for item in t.getmembers():
            assert item.isfile() and not item.issym() and not item.islnk()
            target = new / item.name
            mode = target.stat().st_mode & 0o777 if target.exists() else 0o640
            owner_write(target, t.extractfile(item).read(), owner, mode)
    for name, h in m["backend_files"].items():
        assert sha(new / name) == h, name
    for name, h in m["keys"].items():
        assert sha(new / name) == h
    # All original files, including config and Listening, remain byte-identical unless allowlisted.
    for source in old.rglob("*"):
        rel = source.relative_to(old)
        if (
            ".venv" in rel.parts
            or "__pycache__" in rel.parts
            or not source.is_file()
            or source.is_symlink()
        ):
            continue
        if str(rel) not in allowed:
            assert sha(source) == sha(new / rel), "Unexpected change: " + str(rel)
            x, y = source.stat(), (new / rel).stat()
            assert (x.st_uid, x.st_gid, x.st_mode) == (y.st_uid, y.st_gid, y.st_mode)
    contract = probe(new)
    # Rollback uses original exam/key/code files, with additive lookup for new frozen-snapshot assets.
    subprocess.run(["cp", "-a", str(old), str(rescue)], check=True)
    owner_write(
        rescue / "app/modules/reading/catalog.py",
        (new / "app/modules/reading/catalog.py").read_bytes(),
        owner,
    )
    manifest = json.loads((rescue / "app/content/reading_v1/manifest.json").read_text())
    fresh = json.loads(
        (new / "app/content/reading_v1/exams/cambridge_07/test_01.json").read_text()
    )
    asset = next(
        g
        for g in fresh["passages"][1]["question_groups"]
        if g["question_numbers"][0] == 14
    )["assets"][0]
    owner_write(
        rescue / "app/content/reading_v1" / asset["path"],
        (new / "app/content/reading_v1" / asset["path"]).read_bytes(),
        owner,
    )
    manifest["retained_assets"] = manifest.get("retained_assets", []) + [asset]
    owner_write(
        rescue / "scripts/reading_dataset/validator.py",
        (new / "scripts/reading_dataset/validator.py").read_bytes(),
        owner,
    )
    manifest["generator_sha256"]["validator.py"] = sha(
        rescue / "scripts/reading_dataset/validator.py"
    )
    manifest["content_revision"] = revision(manifest)
    owner_write(
        rescue / "app/content/reading_v1/manifest.json",
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode(),
        owner,
    )
    assert probe(rescue)["reading_catalog"] == "PASS"
    shutil.copyfile(a.meta, backup / "release-meta.json")
    shutil.copyfile(__file__, backup / "release.py")
    (backup / "stage.json").write_text(
        json.dumps(
            {
                "commit": m["commit"],
                "candidate": str(new),
                "original": str(old),
                "rollback_release": str(rescue),
                "catalog": contract,
                "worker_before": m["previous_worker_version"],
                "non_payload_files_unchanged": True,
            },
            indent=2,
        )
    )
    print(
        json.dumps(
            {
                "staged": str(new),
                "backup": str(backup),
                "rollback": str(rescue),
                "catalog": contract,
            }
        )
    )
elif a.action == "activate":
    assert active() == str(old) and (backup / "stage.json").exists()
    try:
        activate(new)
    except Exception:
        activate(rescue)
        raise
    print(
        json.dumps(
            {"backend_release": new.name, "commit": m["commit"], "health": "PASS"}
        )
    )
else:
    assert (
        active() in [str(old), str(new), str(rescue)]
        and (backup / "stage.json").exists()
    )
    activate(rescue)
    print(json.dumps({"rollback": "PASS", "release": rescue.name, "health": "PASS"}))
