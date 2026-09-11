"""Delete orphaned snippets and require ownership."""

from alembic import op
import sqlalchemy as sa

revision = "002_enforce_ownership"
down_revision = "001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM snippets WHERE user_id IS NULL"))
    with op.batch_alter_table("snippets", recreate="always") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("snippets", recreate="always") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
