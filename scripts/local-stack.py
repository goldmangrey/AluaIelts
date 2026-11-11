#!/usr/bin/env python3
"""Persistent, loopback-only Alua development stack; never uses the configured DB."""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / ".local/share/alua/local-stack"
PYTHON = ROOT / "backend/.venv/bin/python"
PG = Path("/opt/homebrew/opt/postgresql@17/bin")


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def start(name, args, cwd, env):
    pidfile = STATE / (name + ".pid")
    if pidfile.exists() and alive(int(pidfile.read_text())):
        print(name + ": already running")
        return
    with (STATE / (name + ".log")).open("ab") as log:
        process = subprocess.Popen(
            [str(a) for a in args],
            cwd=cwd,
            env=env,
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    pidfile.write_text(str(process.pid))


def wait(url):
    for _ in range(90):
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            time.sleep(1)
    raise RuntimeError("Not ready: " + url + "; see logs in " + str(STATE))


def main():
    os.umask(0o077)
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "down":
        for name in ("frontend", "backend"):
            path = STATE / (name + ".pid")
            if path.exists():
                pid = int(path.read_text())
                if alive(pid):
                    os.killpg(pid, signal.SIGTERM)
                path.unlink()
        if (STATE / "postgres/postmaster.pid").exists():
            run([PG / "pg_ctl", "-D", STATE / "postgres", "-m", "fast", "-w", "stop"])
        return
    if action == "status":
        for name in ("frontend", "backend"):
            path = STATE / (name + ".pid")
            print(
                name
                + ": "
                + (
                    "RUNNING"
                    if path.exists() and alive(int(path.read_text()))
                    else "STOPPED"
                )
            )
        print("Frontend: http://localhost:3000")
        print("Backend: http://127.0.0.1:8000/docs")
        print("Private state/logs: " + str(STATE))
        return
    if action != "up":
        raise SystemExit("Usage: python3 scripts/local-stack.py up|down|status")
    for port, name in ((3000, "frontend"), (8000, "backend")):
        path = STATE / (name + ".pid")
        if not (path.exists() and alive(int(path.read_text()))):
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", port))
    # Read public Firebase identifiers without copying or displaying credentials.
    public = {}
    for line in (ROOT / "web/.env.local").read_text().splitlines():
        if line.startswith("NEXT_PUBLIC_") and "=" in line:
            key, value = line.split("=", 1)
            public[key] = value.strip().strip('"').strip("'")
    credential = ROOT / ".secrets/firebase-admin.json"
    if not credential.is_file():
        raise RuntimeError("Existing local Firebase Admin credential is missing")
    if json.loads(credential.read_text()).get("project_id") != public.get(
        "NEXT_PUBLIC_FIREBASE_PROJECT_ID"
    ):
        raise RuntimeError("Local Firebase project mismatch")
    data = STATE / "postgres"
    if not (data / "PG_VERSION").exists():
        run(
            [
                PG / "initdb",
                "-D",
                data,
                "-A",
                "trust",
                "-U",
                "alua_local",
                "--no-locale",
                "--encoding=UTF8",
            ],
            stdout=subprocess.DEVNULL,
        )
    if not (data / "postmaster.pid").exists():
        run(
            [
                PG / "pg_ctl",
                "-D",
                data,
                "-l",
                STATE / "postgres.log",
                "-o",
                f"-k {STATE} -h '' -p 55432",
                "-w",
                "start",
            ]
        )
    # Unix socket only, inside a 0700 directory; no exposed trust-auth TCP server.
    env = os.environ.copy()
    env.update(
        APP_ENV="local",
        DEBUG="false",
        ALUA_LOCAL_STACK="true",
        DATABASE_URL=f"postgresql+psycopg://alua_local@/postgres?host={STATE}&port=55432",
        FIREBASE_AUTH_ENABLED="true",
        LEGACY_AUTH_ENABLED="false",
        FIREBASE_PROJECT_ID=public["NEXT_PUBLIC_FIREBASE_PROJECT_ID"],
        GOOGLE_APPLICATION_CREDENTIALS=str(credential),
        NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000/api/v1",
        READING_AI_WORKER_URL="http://127.0.0.1:3000/api/reading/explain",
        LISTENING_AI_WORKER_URL="http://127.0.0.1:3000/api/listening/explain",
        READING_AI_ENABLED="true",
        READING_AI_CACHE_ROOT=str(STATE / "cache/reading"),
        LISTENING_AI_CACHE_ROOT=str(STATE / "cache/listening"),
        LISTENING_AUDIO_ROOT=str(Path.home() / "Desktop/Listening"),
    )
    env.pop("FIREBASE_AUTH_EMULATOR_HOST", None)
    env.pop("NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_URL", None)
    run([PYTHON, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", env=env)
    start(
        "backend",
        [
            PYTHON,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        ROOT / "backend",
        env,
    )
    wait("http://127.0.0.1:8000/api/v1/health")
    start(
        "frontend",
        [shutil.which("pnpm"), "dev", "--hostname", "127.0.0.1", "--port", "3000"],
        ROOT / "web",
        env,
    )
    wait("http://127.0.0.1:3000/api/alua/health")
    print(
        "READY: http://localhost:3000 — local frontend + backend + persistent PostgreSQL"
    )


if __name__ == "__main__":
    main()
