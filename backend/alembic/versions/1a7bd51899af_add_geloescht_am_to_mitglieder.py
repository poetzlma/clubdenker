"""add geloescht_am to mitglieder

Revision ID: 1a7bd51899af
Revises: 81ffc3647034
Create Date: 2026-03-10 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a7bd51899af'
down_revision: Union[str, None] = '81ffc3647034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('mitglieder', schema=None) as batch_op:
        batch_op.add_column(sa.Column('geloescht_am', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('mitglieder', schema=None) as batch_op:
        batch_op.drop_column('geloescht_am')
