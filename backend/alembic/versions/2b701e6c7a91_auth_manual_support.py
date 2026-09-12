"""add auth, manual data source, and support requests

Revision ID: 2b701e6c7a91
Revises: 980cd04c5ba9
"""
from alembic import op
import sqlalchemy as sa

revision = "2b701e6c7a91"
down_revision = "980cd04c5ba9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customers", sa.Column("data_source", sa.String(length=20), server_default="synthetic", nullable=False))
    op.add_column("transactions", sa.Column("data_source", sa.String(length=20), server_default="synthetic", nullable=False))
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id"), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "support_requests",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("recommendation_id", sa.UUID(), sa.ForeignKey("recommendations.id"), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("linked_audit_log_id", sa.UUID(), sa.ForeignKey("audit_logs.id"), nullable=True),
        sa.Column("status", sa.String(length=15), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("reason IN ('low_confidence','vetoed_recommendation','general_question','dispute')", name="ck_support_reason"),
        sa.CheckConstraint("status IN ('open','resolved')", name="ck_support_status"),
    )
    op.create_index("idx_support_customer_created", "support_requests", ["customer_id", "created_at"])


def downgrade():
    op.drop_index("idx_support_customer_created", table_name="support_requests")
    op.drop_table("support_requests")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_column("transactions", "data_source")
    op.drop_column("customers", "data_source")
