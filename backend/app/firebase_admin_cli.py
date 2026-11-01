"""Private, explicit identity administration. No HTTP provisioning or email matching."""

import argparse
from datetime import UTC, datetime
from uuid import uuid4

from firebase_admin import auth
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.firebase_auth import firebase_app
from app.db.database import get_database
from app.db.models import FirebaseIdentityRow, HouseholdProfileRow, LearnerProfileRow
from app.db.serialization import document
from app.modules.enrollment.bootstrap import ROLES, bind_existing, household_lock
from app.modules.users.models import UserProfile, UserRole


def bind_identity(session: Session, uid: str, learner_id: str) -> None:
    household_lock(session)
    if not 1 <= len(uid) <= 128 or session.get(LearnerProfileRow, learner_id) is None:
        raise ValueError("Expected UID and existing learner")
    if (
        session.scalar(
            select(HouseholdProfileRow).where(HouseholdProfileRow.learner_id == learner_id)
        )
        is None
    ):
        raise ValueError("Learner must have an explicitly assigned household role")
    current = session.get(FirebaseIdentityRow, uid)
    other = session.scalar(
        select(FirebaseIdentityRow).where(FirebaseIdentityRow.learner_id == learner_id)
    )
    if current and current.learner_id == learner_id:
        return
    if current or other:
        raise ValueError("Refusing to replace an existing identity")
    session.add(
        FirebaseIdentityRow(firebase_uid=uid, learner_id=learner_id, created_at=datetime.now(UTC))
    )
    session.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    bind = commands.add_parser("bind")
    bind.add_argument("--firebase-uid", required=True)
    bind.add_argument("--learner-id", required=True)
    bind.add_argument("--apply", action="store_true")
    provision = commands.add_parser("provision-missing-learner")
    provision.add_argument("--role", choices=ROLES, required=True)
    provision.add_argument("--display-name", required=True)
    provision.add_argument("--existing-learner-id")
    provision.add_argument("--confirm-new-profile", action="store_true")
    provision.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        with get_database().session() as session:
            household_lock(session)
            if args.command == "list":
                for learner in session.scalars(select(LearnerProfileRow)):
                    print(learner.learner_id, learner.display_name)
                for row in session.scalars(select(HouseholdProfileRow)):
                    print("role", row.role, row.learner_id)
                for row in session.scalars(select(FirebaseIdentityRow)):
                    print("firebase", row.firebase_uid, "->", row.learner_id)
                return
            if args.command == "bind":
                # Verify account exists in the configured project; passwords are never involved.
                user = auth.get_user(args.firebase_uid, app=firebase_app())
                if user.disabled:
                    raise ValueError("Disabled account")
                bind_identity(session, args.firebase_uid, args.learner_id)
            else:
                if session.get(HouseholdProfileRow, args.role):
                    raise ValueError("Role already exists; use its existing learner")
                if args.existing_learner_id:
                    bind_existing(session, args.role, args.existing_learner_id)
                else:
                    if not args.confirm_new_profile or not args.display_name.strip():
                        raise ValueError(
                            "Explicit confirmation of a genuinely missing learner required"
                        )
                    now = datetime.now(UTC)
                    profile = UserProfile(
                        uid=str(uuid4()),
                        display_name=args.display_name.strip(),
                        role=UserRole.LEARNER,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(
                        LearnerProfileRow(
                            learner_id=profile.uid,
                            display_name=profile.display_name,
                            created_at=now,
                            updated_at=now,
                            payload=document(profile),
                        )
                    )
                    session.flush()
                    bind_existing(session, args.role, profile.uid)
                    if args.apply:
                        print("Created learner:", profile.uid)
            if not args.apply:
                session.rollback()
        print("Applied." if args.apply else "Validated; rolled back (use --apply to persist).")
    except Exception:
        parser.exit(
            1, "No confirmed change. Check project, credentials, existing IDs and constraints.\n"
        )


if __name__ == "__main__":
    main()
