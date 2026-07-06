"""add_topics_json_to_content_items

Revision ID: c3f8a1b2d4e5
Revises: b25ea14286c5
Create Date: 2026-07-06 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f8a1b2d4e5"
down_revision: Union[str, Sequence[str], None] = "b25ea14286c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("content_items", sa.Column("topics_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("content_items", "topics_json")
