"""Track refresh token families for reuse detection.

Revision ID: c4f1d6a8e9b0
Revises: 7d2f8a1c4e90
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "c4f1d6a8e9b0"
down_revision: Union[str, Sequence[str], None] = "7d2f8a1c4e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", sa.String(length=36), nullable=True),
    )

    connection = op.get_bind()
    existing_ids = connection.execute(
        sa.text("SELECT id FROM refresh_tokens WHERE family_id IS NULL")
    ).fetchall()
    for row in existing_ids:
        connection.execute(
            sa.text(
                "UPDATE refresh_tokens SET family_id = :family_id WHERE id = :id"
            ),
            {"family_id": str(uuid4()), "id": row[0]},
        )

    with op.batch_alter_table("refresh_tokens") as batch_op:
        batch_op.alter_column(
            "family_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )

    op.create_index(
        "ix_refresh_tokens_family_id",
        "refresh_tokens",
        ["family_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    with op.batch_alter_table("refresh_tokens") as batch_op:
        batch_op.drop_column("family_id")
