"""add employee manager_id

Revision ID: a1b2c3d4e5f6
Revises: 7f125d93f175
Create Date: 2026-06-08 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7f125d93f175"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("manager_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_employees_manager_id",
        "employees",
        "employees",
        ["manager_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_employees_manager_id"), "employees", ["manager_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_employees_manager_id"), table_name="employees")
    op.drop_constraint("fk_employees_manager_id", "employees", type_="foreignkey")
    op.drop_column("employees", "manager_id")
