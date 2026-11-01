"""Allowlisted Firebase identities attached to existing learners."""

import sqlalchemy as sa

from alembic import op

revision = "20261101_0006"
down_revision = "20261101_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision 0001 creates current Base.metadata on fresh installations.
    if sa.inspect(op.get_bind()).has_table("firebase_identities"):
        return
    op.create_table(
        "firebase_identities",
        sa.Column("firebase_uid", sa.String(128), primary_key=True),
        sa.Column(
            "learner_id",
            sa.String(36),
            sa.ForeignKey("learner_profiles.learner_id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    pass  # Keep identity bindings on application rollback; legacy access remains available.
