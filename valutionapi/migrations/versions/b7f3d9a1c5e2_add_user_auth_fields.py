"""add user auth fields

Revision ID: b7f3d9a1c5e2
Revises: dcdc1d3fc2cb
Create Date: 2026-06-04 13:29:45.487000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f3d9a1c5e2"
down_revision: Union[str, Sequence[str], None] = "dcdc1d3fc2cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("role", sa.String(), nullable=False, server_default=sa.text("'user'"))
        )
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"))
        )
        batch_op.add_column(sa.Column("last_login", sa.DateTime(), nullable=True))
        batch_op.create_unique_constraint("uq_users_email", ["email"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.drop_column("last_login")
        batch_op.drop_column("is_active")
        batch_op.drop_column("role")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("email")
