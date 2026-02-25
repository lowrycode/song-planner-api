"""Add title and thumbnail_key to song_youtube_links table

Revision ID: 7071f87f7a25
Revises: fe5dc26c3f66
Create Date: 2026-02-25 12:38:06.431134

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7071f87f7a25"
down_revision: Union[str, Sequence[str], None] = "fe5dc26c3f66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Title - use temporary server_default, then remove
    op.add_column(
        "song_youtube_links",
        sa.Column(
            "title", sa.String(length=255), nullable=False, server_default="Untitled"
        ),
    )
    op.alter_column("song_youtube_links", "title", server_default=None)

    # Thumbnail Key
    op.add_column(
        "song_youtube_links",
        sa.Column("thumbnail_key", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("song_youtube_links", "thumbnail_key")
    op.drop_column("song_youtube_links", "title")
