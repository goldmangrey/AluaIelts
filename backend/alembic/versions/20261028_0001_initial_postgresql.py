"""Initial Alua PostgreSQL schema.

Revision ID: 20261028_0001
Revises: None
"""

from sqlalchemy import text

from alembic import op
from app.db.models import Base

revision = "20261028_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)
    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_partner_active_learner "
                "ON partner_relationships (learner_id) WHERE status = 'active'"
            )
        )
        op.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_partner_active_partner "
                "ON partner_relationships (partner_id) WHERE status = 'active'"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
