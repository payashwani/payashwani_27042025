"""Add local_time and prev_status to store_status

Revision ID: your_revision_id_here  # Replace with the actual ID (e.g., '123abcd456ef')
Revises: base  # Or the actual down_revision if it's not the first
Create Date: ... (The timestamp will be here)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'your_revision_id_here'  # REPLACE THIS WITH THE ACTUAL ID
down_revision: Union[str, None] = 'base'  # Or the actual down_revision
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('store_status', sa.Column('local_time', sa.DateTime()))
    op.add_column('store_status', sa.Column('prev_status', sa.String(length=255)))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('store_status', 'prev_status')
    op.drop_column('store_status', 'local_time')