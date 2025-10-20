"""Added point field

Revision ID: 059de3bcdcd9
Revises: 4deea68a57b2
Create Date: 2025-09-29 17:42:36.304011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '059de3bcdcd9'
down_revision: Union[str, None] = '4deea68a57b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
