"""Create the phase-four storage model."""

from pathlib import Path
from alembic import op

revision = "0001_foundation"
down_revision = None


def upgrade():
    op.execute(Path(__file__).with_suffix(".sql").read_text())


def downgrade():
    op.execute(
        "DROP TABLE ingestion_runs, raw_items, niche_stats, niches, card_sources, cards, traces_index, approvals, conversations, dimension_scores, verdicts, runs, idea_versions, ideas, profiles, users"
    )
