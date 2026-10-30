"""Add permanent study assignments and idempotent study actions."""

from alembic import op
from app.db.models import StudyEventRow, StudyProgramRow

revision = "20261031_0004"
down_revision = "20261030_0003"
branch_labels = None
depends_on = None


def upgrade():
    for table in (StudyProgramRow.__table__, StudyEventRow.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    pass  # Never discard a learner's book on application rollback.
