"""Vocabulary V1 shared learned state and idempotent actions. No content import."""

from alembic import op
from app.modules.vocabulary_v1.models import (
    VocabularyActionRow,
    VocabularyDayRow,
    VocabularyLearnedRow,
)

revision = "20261114_0009"
down_revision = "20261111_0008"
branch_labels = None
depends_on = None


def upgrade():
    for model in (VocabularyLearnedRow, VocabularyActionRow, VocabularyDayRow):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    pass  # Preserve learner history, matching existing additive migrations.
