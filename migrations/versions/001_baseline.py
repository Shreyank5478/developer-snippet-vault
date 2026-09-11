"""Create the snippet vault schema or baseline an existing schema."""

from alembic import op
import sqlalchemy as sa

revision = "001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("api_key_hash", sa.String(length=64), nullable=False),
            sa.UniqueConstraint("api_key_hash"),
        )
    if "snippets" not in tables:
        op.create_table(
            "snippets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("code", sa.Text(), nullable=False),
            sa.Column("category", sa.String(length=40), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
    else:
        columns = {column["name"] for column in inspector.get_columns("snippets")}
        if "user_id" not in columns:
            op.add_column("snippets", sa.Column("user_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_table("snippets")
    op.drop_table("users")
