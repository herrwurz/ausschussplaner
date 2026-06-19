"""Add User authentication model.

Revision ID: a2b3c4d5e6f7
Revises: 9023635ce003
Create Date: 2026-06-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a2b3c4d5e6f7"
down_revision = "9023635ce003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("vorname", sa.String(100), nullable=False),
        sa.Column("nachname", sa.String(100), nullable=False),
        sa.Column("rolle", sa.String(50), nullable=False, server_default="benutzer"),
        sa.Column("obmann_ausschuss_ids", sa.String(500), nullable=False, server_default=""),
        sa.Column("aktiv", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )


def downgrade() -> None:
    op.drop_table("user")
