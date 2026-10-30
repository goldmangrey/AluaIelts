"""Add two permanent household aliases without rewriting learner IDs or progress."""

from alembic import op
from app.db.models import HouseholdProfileRow

revision = "20261029_0002"
down_revision = "20261028_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Initial migration uses current metadata; checkfirst also supports fresh installs.
    HouseholdProfileRow.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Preserve learner profiles, devices and every progress table.
    HouseholdProfileRow.__table__.drop(op.get_bind(), checkfirst=True)
