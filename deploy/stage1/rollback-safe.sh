#!/bin/bash
# Alua-only rollback. Never selects the original insecure backend-next directory.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo'; exit 1; }
RELEASE=/opt/alua/releases/pre-s1-safe-20261029
test -x "$RELEASE/.venv/bin/python"
grep -Fq 'raise NotFoundError(message="Bootstrap disabled.", code="bootstrap_disabled")' "$RELEASE/app/modules/enrollment/router.py"
cat > /etc/systemd/system/alua-api.service.d/20-stage1-release.conf <<EOF
[Service]
WorkingDirectory=$RELEASE
ExecStart=
ExecStart=$RELEASE/.venv/bin/python -B -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --proxy-headers --forwarded-allow-ips=127.0.0.1 --no-access-log
EOF
systemctl daemon-reload
systemctl restart alua-api.service
for attempt in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8010/api/v1/health >/dev/null 2>&1; then break; fi
    sleep 1
done
curl -fsS http://127.0.0.1:8010/api/v1/health >/dev/null
status=$(curl -sS -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' --data '{"role":"wife","device_secret":"0000000000000000000000000000000000000000000000000000000000000000"}' http://127.0.0.1:8010/api/v1/bootstrap)
[[ "$status" == 404 ]] || { systemctl stop alua-api.service; echo 'Safety check failed: Alua stopped'; exit 1; }
echo 'Safe rollback active; bootstrap disabled. Database unchanged.'
