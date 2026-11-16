"""Review state only; no copied attempts or result mutations."""

from sqlalchemy import inspect

from alembic import op
from app.modules.practice.models import MistakeStateRow

revision = "20261115_0011"
down_revision = "20261115_0010"
branch_labels = None
depends_on = None


def upgrade():
    MistakeStateRow.__table__.create(op.get_bind(), checkfirst=True)
    for table, owner in [
        ("listening_attempts", "learner_id"),
        ("reading_attempts", "learner_id"),
        ("writing_attempts", "owner"),
    ]:
        name = "ix_" + table + "_owner_updated"
        if name not in {i["name"] for i in inspect(op.get_bind()).get_indexes(table)}:
            op.create_index(name, table, [owner, "updated_at"])


def downgrade():
    pass  # Preserve review work and all historical results.
