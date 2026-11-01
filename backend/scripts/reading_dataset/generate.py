"""Transactional generation: failed parsing or validation leaves prior dataset intact."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from engine import DEST, build, write
from validator import validate


def generate(destination: Path):
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Schemas and documentation are authored canonically, not inferred from generated data.
    template = destination if (destination / "schema").exists() else DEST
    with tempfile.TemporaryDirectory(prefix=".reading-build-", dir=destination.parent) as temporary:
        work = Path(temporary)
        stage = work / "dataset"
        stage.mkdir()
        shutil.copytree(template / "schema", stage / "schema")
        if (template / "README.md").exists():
            shutil.copy2(template / "README.md", stage / "README.md")
        build(stage)
        result = validate(stage)
        if not result["artifact_validation_passed"]:
            raise ValueError("Staged dataset failed validation; previous dataset preserved")
        import json

        audit = json.loads((stage / "audit_report.json").read_text())
        audit["validation"] = result
        write(stage / "audit_report.json", audit)
        backup = work / "previous"
        had_previous = destination.exists()
        if had_previous:
            os.replace(destination, backup)
        try:
            os.replace(stage, destination)
        except BaseException:
            if had_previous:
                os.replace(backup, destination)
            raise
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=DEST)
    generate(ap.parse_args().output)
