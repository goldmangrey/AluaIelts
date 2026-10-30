"""Private administration; never run through HTTP or log code output."""

import argparse
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.db.database import get_database
from app.db.models import (
    DeviceEnrollmentRow,
    EnrollmentCodeRow,
    HouseholdProfileRow,
    LearnerProfileRow,
)
from app.modules.enrollment.bootstrap import household_lock
from app.modules.enrollment.repository import hash_secret


def main() -> None:
    parser = argparse.ArgumentParser(description="Alua private device administration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-household-candidates")
    create = commands.add_parser("create-enrollment-code")
    create.add_argument("--learner-id", required=True)
    create.add_argument("--ttl-minutes", type=int, default=15, choices=range(1, 31))
    create.add_argument(
        "--output", type=Path, required=True, help="New private file (0600); never stdout"
    )
    confirm = commands.add_parser("confirm-household-devices")
    confirm.add_argument("--husband-enrollment-id", required=True)
    confirm.add_argument("--wife-enrollment-id", required=True)
    confirm.add_argument("--apply", action="store_true", help="Default is validation only")
    args = parser.parse_args()
    output_created = False
    try:
        with get_database().session() as session:
            household_lock(session)
            households = {
                r.role: r.learner_id for r in session.scalars(select(HouseholdProfileRow))
            }
            if args.command == "list-household-candidates":
                for row in session.scalars(
                    select(LearnerProfileRow).order_by(LearnerProfileRow.created_at)
                ):
                    print(f"{row.learner_id}  {row.display_name}")
                for role, uid in sorted(households.items()):
                    print(f"{role} -> {uid}")
                return
            if args.command == "create-enrollment-code":
                learner = session.get(LearnerProfileRow, args.learner_id)
                if learner is None or args.learner_id not in households.values():
                    raise ValueError("Expected an existing household learner ID")
                now = datetime.now(UTC)
                # 128 random bits, copy/paste-friendly ASCII; store only SHA-256.
                code = secrets.token_hex(16).upper()
                session.add(
                    EnrollmentCodeRow(
                        code_hash=hash_secret(code),
                        learner_id=learner.learner_id,
                        display_name=learner.display_name,
                        created_at=now,
                        expires_at=now + timedelta(minutes=args.ttl_minutes),
                    )
                )
                fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                output_created = True
                with os.fdopen(fd, "w") as stream:
                    stream.write(code + "\n")
            else:
                keep = {"husband": args.husband_enrollment_id, "wife": args.wife_enrollment_id}
                if set(households) != {"husband", "wife"} or len(set(households.values())) != 2:
                    raise ValueError("Two distinct existing household profiles are required")
                rows = list(
                    session.scalars(
                        select(DeviceEnrollmentRow)
                        .order_by(DeviceEnrollmentRow.enrollment_id)
                        .with_for_update()
                    )
                )
                by_id = {row.enrollment_id: row for row in rows}
                for role, eid in keep.items():
                    row = by_id.get(eid)
                    if (
                        row is None
                        or row.revoked_at is not None
                        or row.learner_id != households[role]
                    ):
                        raise ValueError(f"Invalid active enrollment for {role}; nothing changed")
                others = [
                    row
                    for row in rows
                    if row.revoked_at is None and row.enrollment_id not in keep.values()
                ]
                print(f"Validated two devices. Other active enrollments: {len(others)}")
                if args.apply:
                    now = datetime.now(UTC)
                    for row in others:
                        row.revoked_at = now
                    # Outstanding codes must not reopen access after pruning.
                    for code_row in session.scalars(
                        select(EnrollmentCodeRow)
                        .where(EnrollmentCodeRow.redeemed_at.is_(None))
                        .with_for_update()
                    ):
                        code_row.expires_at = now
        print(
            "Completed."
            if args.command == "create-enrollment-code" or args.apply
            else "Validation only; no changes."
        )
    except Exception:
        if output_created:
            args.output.unlink(missing_ok=True)
        # Avoid SQL parameter values or credentials appearing in CLI tracebacks.
        parser.exit(
            1,
            "Administration failed; success not confirmed. Check IDs and database availability.\n",
        )


if __name__ == "__main__":
    main()
