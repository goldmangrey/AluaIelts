"""Add learner-scoped diagnostic and content preferences; preserve all history."""

from alembic import op
from app.db.models import LearningQualityRow

revision = "20261030_0003"
down_revision = "20261029_0002"
branch_labels = None
depends_on = None


def upgrade():
    # Initial revision creates current metadata on fresh databases.
    LearningQualityRow.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    # Deliberately retain additive learning history when rolling application code back.
    pass
