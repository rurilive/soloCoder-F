"""add growth_standards table

Revision ID: 52aa7ccfdbac
Revises: b9fcc070a811
Create Date: 2026-05-04 16:21:19.608511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52aa7ccfdbac'
down_revision: Union[str, Sequence[str], None] = 'b9fcc070a811'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    from sqlalchemy.engine import Engine
    
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if not inspector.has_table('growth_standards'):
        op.create_table(
            'growth_standards',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('gender', sa.String(length=10), nullable=True),
            sa.Column('age_months', sa.Integer(), nullable=True),
            sa.Column('measurement_type', sa.String(length=20), nullable=True),
            sa.Column('p3', sa.Float(), nullable=True),
            sa.Column('p15', sa.Float(), nullable=True),
            sa.Column('p50', sa.Float(), nullable=True),
            sa.Column('p85', sa.Float(), nullable=True),
            sa.Column('p97', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_growth_standards_age_months'), 'growth_standards', ['age_months'], unique=False)
        op.create_index(op.f('ix_growth_standards_gender'), 'growth_standards', ['gender'], unique=False)
        op.create_index(op.f('ix_growth_standards_id'), 'growth_standards', ['id'], unique=False)
        op.create_index(op.f('ix_growth_standards_measurement_type'), 'growth_standards', ['measurement_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_growth_standards_measurement_type'), table_name='growth_standards')
    op.drop_index(op.f('ix_growth_standards_id'), table_name='growth_standards')
    op.drop_index(op.f('ix_growth_standards_gender'), table_name='growth_standards')
    op.drop_index(op.f('ix_growth_standards_age_months'), table_name='growth_standards')
    op.drop_table('growth_standards')
