"""Read-only fingerprints; prints counts/digests, never record payloads or credentials."""

import json
import subprocess
import sys

args = sys.argv[1:]


def query(sql):
    return subprocess.check_output(
        [
            "runuser",
            "-u",
            "postgres",
            "--",
            "psql",
            "-XAt",
            "-v",
            "ON_ERROR_STOP=1",
            *args,
            "-c",
            sql,
        ],
        text=True,
    ).strip()


def ident(value):
    return '"' + value.replace('"', '""') + '"'


result = {}
for table in query(
    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
).splitlines():
    q = ident(table)
    counts = query(
        f"SELECT count(*), md5(coalesce(string_agg(h, ',' ORDER BY h), '')) FROM (SELECT md5(row_to_json(t)::text) h FROM public.{q} t) s"
    )
    item = {"count": int(counts.split("|")[0]), "digest": counts.split("|")[1]}
    has_learner = query(
        f"SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='{table}' AND column_name='learner_id'"
    )
    if has_learner == "1":
        item["per_learner"] = query(
            f"SELECT learner_id,count(*) FROM public.{q} GROUP BY learner_id ORDER BY learner_id"
        ).splitlines()
    result[table] = item
print(json.dumps(result, indent=2, sort_keys=True))
