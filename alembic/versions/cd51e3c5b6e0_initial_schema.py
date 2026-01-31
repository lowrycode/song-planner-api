""" Initial schema: enable pgvector extension

Revision ID: cd51e3c5b6e0
Revises: None
Create Date: 2025-12-16 19:19:44.788484

"""
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'cd51e3c5b6e0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Optional: remove pgvector on downgrade
    op.execute("DROP EXTENSION IF EXISTS vector")
