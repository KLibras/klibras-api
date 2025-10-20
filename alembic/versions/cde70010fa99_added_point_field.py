"""Added point field

Revision ID: cde70010fa99
Revises: 059de3bcdcd9
Create Date: 2025-09-29 18:19:13.423055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cde70010fa99'
down_revision: Union[str, None] = '059de3bcdcd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
