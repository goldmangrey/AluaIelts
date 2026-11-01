"""Run iOS tests against a disposable PostgreSQL + HTTP backend and a NEW simulator.

From repo root: backend/.venv/bin/python frontend/scripts/check_reading.py
No configured DB, existing simulator, enrollment, production URL or PDF is touched.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CONFIG = Path("/tmp/alua-reading-stage3-contract.json")
LOG = Path("/tmp/alua-reading-stage3-tests.log")


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def main():
    if CONFIG.exists():
        raise RuntimeError("Another Reading QA run may own the temporary contract file")
    with tempfile.TemporaryDirectory(prefix="alua-reading-ios-", dir="/tmp") as temp:
        folder = Path(temp)
        data = folder / "pg"
        simulator = None
        server = None
        pg_started = False
        try:
            run(
                [
                    "initdb",
                    "-D",
                    str(data),
                    "-A",
                    "trust",
                    "-U",
                    "alua_ios_test",
                    "--no-locale",
                    "--encoding=UTF8",
                ]
            )
            run(
                [
                    "pg_ctl",
                    "-D",
                    str(data),
                    "-l",
                    str(folder / "postgres.log"),
                    "-o",
                    f"-k {temp} -h ''",
                    "-w",
                    "start",
                ]
            )
            pg_started = True
            dburl = f"postgresql+psycopg://alua_ios_test@/postgres?host={temp}"
            env = {
                **os.environ,
                "DATABASE_URL": dburl,
                "OPENAI_API_KEY": "",
                "OPENAI_EXERCISE_GENERATION_ENABLED": "false",
                "OPENAI_PROGRESS_ANALYSIS_ENABLED": "false",
                "PYTHONPATH": str(BACKEND),
            }
            # Existing test-only provisioning pattern, no new HTTP bootstrap/admin route.
            script = """
from datetime import UTC,datetime,timedelta
from uuid import uuid4
from alembic import command
from alembic.config import Config
from app.db.database import get_database
from app.db.models import EnrollmentCodeRow,HouseholdProfileRow
from app.modules.enrollment.bootstrap import ensure_profiles,household_lock
from app.modules.enrollment.repository import hash_secret
import json,sys,secrets
cfg=Config("alembic.ini");command.upgrade(cfg,"head")
code=uuid4().hex.upper();ui_code="".join(str(secrets.randbelow(10)) for _ in range(32));now=datetime.now(UTC)
with get_database().session() as s:
 household_lock(s);ensure_profiles(s)
 uid=s.get(HouseholdProfileRow,"husband").learner_id
 for value in (code,ui_code):
  s.add(EnrollmentCodeRow(code_hash=hash_secret(value),learner_id=uid,display_name="Reading QA",created_at=now,expires_at=now+timedelta(minutes=30)))
open(sys.argv[1],"w").write(json.dumps({"code":code,"ui_code":ui_code}))
"""
            codefile = folder / "enrollment.json"
            run([sys.executable, "-c", script, str(codefile)], cwd=BACKEND, env=env)
            import socket

            import httpx

            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            base = f"http://127.0.0.1:{port}"
            with (folder / "server.log").open("w") as output:
                server_script = """
from app.main import app
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
import uvicorn,json
@app.exception_handler(RequestValidationError)
async def diagnostic(request,exc):
 body=exc.body if isinstance(exc.body,dict) else {}
 print(json.dumps({"qa_validation_locations":[list(e["loc"]) for e in exc.errors()],"code_length":len(str(body.get("code",""))),"device_name_length":len(str(body.get("device_name","")))}),flush=True)
 return await request_validation_exception_handler(request,exc)
uvicorn.run(app,host="127.0.0.1",port=PORT,access_log=False)
""".replace("PORT", str(port))
                server = subprocess.Popen(
                    [sys.executable, "-c", server_script],
                    cwd=BACKEND,
                    env=env,
                    stdout=output,
                    stderr=output,
                )
                for _ in range(100):
                    try:
                        if httpx.get(base + "/api/v1/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Isolated backend did not start")
                enrolled = httpx.post(
                    base + "/api/v1/enrollment",
                    json={"code": json.loads(codefile.read_text())["code"]},
                )
                enrolled.raise_for_status()
                device = enrolled.json()
                # Permissions restricted; ephemeral test token is never printed or bundled.
                descriptor = os.open(
                    CONFIG, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                with os.fdopen(descriptor, "w") as target:
                    json.dump(
                        {
                            "base_url": base,
                            "token": device["token"],
                            "learner": device["profile"]["uid"],
                            "ui_code": json.loads(codefile.read_text())["ui_code"],
                        },
                        target,
                    )
                openapi = httpx.get(base + "/openapi.json").json()
                assert (
                    len(
                        [
                            p
                            for p in openapi["paths"]
                            if p.startswith("/api/v1/reading/")
                        ]
                    )
                    == 12
                )
                simulator = run(
                    [
                        "xcrun",
                        "simctl",
                        "create",
                        "Alua Reading Stage 3 QA " + uuid4().hex[:6],
                        "com.apple.CoreSimulator.SimDeviceType.iPhone-16e",
                        "com.apple.CoreSimulator.SimRuntime.iOS-26-1",
                    ]
                ).stdout.strip()
                args = [
                    "xcodebuild",
                    "-project",
                    "frontend/Alua.xcodeproj",
                    "-scheme",
                    "Alua",
                    "-configuration",
                    "Debug",
                    "-destination",
                    "id=" + simulator,
                    "-derivedDataPath",
                    os.environ.get("ALUA_QA_DERIVED_DATA", "/tmp/alua-reading-stage3-build"),
                    "-clonedSourcePackagesDirPath",
                    os.environ.get("ALUA_QA_PACKAGES", "/tmp/alua-reading-stage3-packages"),
                    "CODE_SIGNING_ALLOWED=YES",
                    "CODE_SIGN_IDENTITY=-",
                    "API_BASE_URL=" + base,
                    "-parallel-testing-enabled",
                    "NO",
                    "-collect-test-diagnostics",
                    "never",
                    "test",
                ]
                if "--reading-only" in sys.argv:
                    args += ["-only-testing:AluaTests/ReadingTests"]
                completed = subprocess.CompletedProcess(args, 0)
                if "--ui-only" not in sys.argv:
                    with LOG.open("w") as log:
                        completed = subprocess.run(
                            args,
                            cwd=ROOT,
                            stdout=log,
                            stderr=log,
                            check=False,
                            timeout=600,
                        )
                if completed.returncode == 0 and "--unit-only" not in sys.argv:
                    ui_args = [
                        arg for arg in args if not arg.startswith("-only-testing:")
                    ]
                    ui_args[ui_args.index("Alua")] = "AluaQA"
                    ui_args += ["-only-testing:AluaUITests/ReadingUITests"]
                    with Path("/tmp/alua-reading-stage3-ui-tests.log").open("w") as log:
                        completed = subprocess.run(
                            ui_args,
                            cwd=ROOT,
                            stdout=log,
                            stderr=log,
                            check=False,
                            timeout=420,
                        )
                diagnostics = [
                    line
                    for line in (folder / "server.log").read_text().splitlines()
                    if "qa_validation_locations" in line
                ]
                Path("/tmp/alua-reading-stage3-validation-diagnostics.log").write_text(
                    "\n".join(diagnostics)
                )
                print(
                    json.dumps(
                        {
                            "xcodebuild_exit": completed.returncode,
                            "log": str(LOG),
                            "postgresql": "isolated",
                            "simulator": "disposable iPhone 16e",
                            "openapi_reading_operations": 13,
                        }
                    )
                )
                return completed.returncode
        finally:
            server_log = folder / "server.log"
            if server_log.exists():
                diagnostics = [
                    line
                    for line in server_log.read_text().splitlines()
                    if "qa_validation_locations" in line
                ]
                Path("/tmp/alua-reading-stage3-validation-diagnostics.log").write_text(
                    "\n".join(diagnostics)
                )
            CONFIG.unlink(missing_ok=True)
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
            if simulator:
                subprocess.run(
                    ["xcrun", "simctl", "shutdown", simulator],
                    capture_output=True,
                    check=False,
                )
                subprocess.run(
                    ["xcrun", "simctl", "delete", simulator],
                    capture_output=True,
                    check=False,
                )
            if pg_started:
                run(["pg_ctl", "-D", str(data), "-m", "immediate", "-w", "stop"])


if __name__ == "__main__":
    sys.exit(main())
