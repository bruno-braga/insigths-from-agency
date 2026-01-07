"""add memory table

Revision ID: fd72e91943c0
Revises: 99cbda61c480
Create Date: 2026-01-05 22:50:37.334759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd72e91943c0'
down_revision: Union[str, Sequence[str], None] = '99cbda61c480'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=True),
        sa.Column('memory', sa.Text(), nullable=True),
        sa.Column('create_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('memories')
    pass
