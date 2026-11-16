"""Saved reviews, bounded avatar storage, Speaking completions; additive only."""

from sqlalchemy import inspect

from alembic import op
from app.modules.practice.models import AvatarRow, SavedReviewRow, SpeakingAttemptRow

revision = "20261115_0010"
down_revision = "20261114_0009"
branch_labels = None
depends_on = None


def upgrade():
    for model in (SavedReviewRow, SpeakingAttemptRow, AvatarRow):
        model.__table__.create(op.get_bind(), checkfirst=True)
    for table, owner, completed in (
        ("listening_attempts", "learner_id", "submitted_at"),
        ("reading_attempts", "learner_id", "submitted_at"),
        ("writing_attempts", "owner", "completed_at"),
    ):
        if table == "writing_attempts":
            import sqlalchemy as sa

            if "completed_at" not in {c["name"] for c in inspect(op.get_bind()).get_columns(table)}:
                op.add_column(
                    table, sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
                )
            # Historical update timestamps can be AI retries, not completion times.
            # Preserve their explicit uncertainty: history falls back without inventing a date.
        name = "ix_" + table + "_owner_completed"
        if name not in {i["name"] for i in inspect(op.get_bind()).get_indexes(table)}:
            op.create_index(name, table, [owner, completed])


def downgrade():
    pass  # Never destroy historical attempts, saved reviews or user avatars.
