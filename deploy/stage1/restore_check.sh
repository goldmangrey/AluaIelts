#!/bin/bash
# Validate only a supplied Alua dump in a NEW private PostgreSQL cluster.
set -euo pipefail
umask 077
[[ $# == 1 && -f "$1" ]] || exit 2
ALUA_RESTORE=$(mktemp -d /tmp/alua-backup-restore.XXXXXX)
chown postgres:postgres "$ALUA_RESTORE"
cleanup() {
  runuser -u postgres -- /usr/lib/postgresql/17/bin/pg_ctl -D "$ALUA_RESTORE/data" -m fast -w stop >/dev/null 2>&1 || true
  rm -rf -- "$ALUA_RESTORE"
}
trap cleanup EXIT
install -o postgres -g postgres -m 600 "$1" "$ALUA_RESTORE/alua.dump"
runuser -u postgres -- /usr/lib/postgresql/17/bin/initdb -D "$ALUA_RESTORE/data" -A trust --no-locale --encoding=UTF8 >/dev/null
runuser -u postgres -- /usr/lib/postgresql/17/bin/pg_ctl -D "$ALUA_RESTORE/data" -l "$ALUA_RESTORE/server.log" -o "-k $ALUA_RESTORE -h '' -p 65432 -c shared_buffers=32MB -c max_connections=10" -w start >/dev/null
runuser -u postgres -- createdb -h "$ALUA_RESTORE" -p 65432 alua_restore
runuser -u postgres -- pg_restore --exit-on-error --no-owner --no-privileges -h "$ALUA_RESTORE" -p 65432 -d alua_restore "$ALUA_RESTORE/alua.dump"
runuser -u postgres -- psql -XAt -v ON_ERROR_STOP=1 -h "$ALUA_RESTORE" -p 65432 -d alua_restore -c 'SELECT count(*) FROM learner_profiles; SELECT count(*) FROM household_profiles; SELECT count(*) FROM device_enrollments;' >/dev/null
printf 'Alua isolated restore passed\n'
