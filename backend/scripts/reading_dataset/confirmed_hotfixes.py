"""Hash-bound V1 confirmed repairs, applied after existing source-reviewed overlays.

Question identities are immutable. Explicit, source-reviewed input-type transitions
only affect new snapshots. Historical assets retain their original IDs and bytes.
"""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from repairs import fingerprint


def records():
    from engine import ROOT

    data = json.loads(Path(__file__).with_suffix(".json").read_text())
    ids = [r["target_id"] for r in data["repairs"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate confirmed hotfix target")
    for row in data["repairs"]:
        for field, hash_field in (("pdf_file", "pdf_sha256"), ("txt_file", "txt_sha256")):
            path = (ROOT / row[field]).resolve()
            allowed = ROOT / ("ieltsbooks" if field == "pdf_file" else "ieltsReading")
            if not path.is_relative_to(allowed):
                raise ValueError("Invalid hotfix source path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != row[hash_field]:
                raise ValueError("Confirmed hotfix source changed: " + row[field])
    return data


def retained_assets():
    return copy.deepcopy(records()["retained_assets"])


def materialize_assets(data, base):
    from engine import DEST

    assets = data["retained_assets"] + [
        a for row in data["repairs"] for a in row["set"].get("assets", [])
    ]
    for asset in assets:
        path = Path(asset["path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Invalid hotfix asset path")
        source, destination = DEST / path, Path(base) / path
        # Newly rendered assets already present in a staging tree need no copy.
        if (
            destination.exists()
            and hashlib.sha256(destination.read_bytes()).hexdigest() == asset["sha256"]
        ):
            continue
        if hashlib.sha256(source.read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError("Confirmed hotfix asset changed: " + str(path))
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copyfile(source, destination)


def apply_confirmed_hotfixes(exam, base):
    data = records()
    targets = {p["id"]: p for p in exam["passages"]}
    targets.update({g["id"]: g for p in exam["passages"] for g in p["question_groups"]})
    relevant = [r for r in data["repairs"] if r["exam_id"] == exam["id"]]
    for row in relevant:
        target = targets[row["target_id"]]
        before = target["content"] if row["kind"] == "passage" else target
        current = fingerprint(before)
        if current == row["after_sha256"]:
            continue
        if current not in row["before_sha256"]:
            raise ValueError("Confirmed repair target changed; recheck source: " + row["target_id"])
        allowed = (
            {"content"}
            if row["kind"] == "passage"
            else {
                "instructions",
                "content_blocks",
                "constraints",
                "options",
                "questions",
                "assets",
                "representation",
                "source_reference",
            }
        )
        if not set(row["set"]).issubset(allowed):
            raise ValueError("Unsupported confirmed hotfix field")
        previous = {
            q["id"]: (q["number"], q["answer_input_type"]) for q in target.get("questions", [])
        }
        patched = {**target, **copy.deepcopy(row["set"])}
        following = {
            q["id"]: (q["number"], q["answer_input_type"]) for q in patched.get("questions", [])
        }
        if previous.keys() != following.keys():
            raise ValueError("Hotfix changed question IDs")
        for qid, (number, input_type) in previous.items():
            if following[qid][0] != number:
                raise ValueError("Hotfix changed question number")
            transition = [input_type, following[qid][1]]
            if transition[0] != transition[1] and transition not in row["input_type_transitions"]:
                raise ValueError("Unreviewed hotfix input type transition")
        target.update(copy.deepcopy(row["set"]))
        after = target["content"] if row["kind"] == "passage" else target
        if fingerprint(after) != row["after_sha256"]:
            raise ValueError("Confirmed repair output mismatch")
    if relevant:
        materialize_assets(data, base)
