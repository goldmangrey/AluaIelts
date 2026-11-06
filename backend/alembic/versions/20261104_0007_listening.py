"""Add independent Listening tables; preserve history on rollback."""

from alembic import op
from app.modules.listening.models import (
    ListeningAttemptRow,
    ListeningGrantRow,
    ListeningMutationRow,
)

revision = "20261104_0007"
down_revision = "20261101_0006"
branch_labels = None
depends_on = None


def upgrade():
    for table in (
        ListeningAttemptRow.__table__,
        ListeningMutationRow.__table__,
        ListeningGrantRow.__table__,
    ):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    pass  # Application rollback must not erase user attempts.
