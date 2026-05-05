"""add albums and photos tables

Revision ID: 7d8e9f0a1b2c
Revises: 52aa7ccfdbac
Create Date: 2026-05-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d8e9f0a1b2c'
down_revision: Union[str, Sequence[str], None] = '52aa7ccfdbac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    from sqlalchemy.engine import Engine
    
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if not inspector.has_table('albums'):
        op.create_table(
            'albums',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('baby_id', sa.Integer(), nullable=True),
            sa.Column('name', sa.String(length=100), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('cover_photo_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['baby_id'], ['babies.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_albums_id'), 'albums', ['id'], unique=False)
    
    if not inspector.has_table('photos'):
        op.create_table(
            'photos',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('album_id', sa.Integer(), nullable=True),
            sa.Column('baby_id', sa.Integer(), nullable=True),
            sa.Column('file_path', sa.String(length=255), nullable=True),
            sa.Column('file_name', sa.String(length=255), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('photo_date', sa.Date(), nullable=True),
            sa.Column('tags', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['album_id'], ['albums.id'], ),
            sa.ForeignKeyConstraint(['baby_id'], ['babies.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_photos_id'), 'photos', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_photos_id'), table_name='photos')
    op.drop_table('photos')
    op.drop_index(op.f('ix_albums_id'), table_name='albums')
    op.drop_table('albums')