"""Add Writing tables without altering existing data."""

from alembic import op
from app.modules.writing.models import WritingAttemptRow, WritingTaskRow

revision = "20261111_0008"
down_revision = "20261104_0007"
branch_labels = None
depends_on = None


def upgrade():
    for table in (WritingTaskRow.__table__, WritingAttemptRow.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    pass  # Preserve learner history on application rollback.
