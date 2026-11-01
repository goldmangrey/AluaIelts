"""Add private Reading attempts and idempotent mutations.

Revision ID: 20261101_0005
Revises: 20261031_0004
"""

from alembic import op
from app.modules.reading.models import ReadingAttemptRow, ReadingMutationRow

revision = "20261101_0005"
down_revision = "20261031_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in (ReadingAttemptRow.__table__, ReadingMutationRow.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    pass  # Preserve learning history on application rollback, as in revision 0004.
