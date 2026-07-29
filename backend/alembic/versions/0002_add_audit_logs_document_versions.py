"""add audit_logs_immutable, document_versions, prompt_versions

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs_immutable",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("status_code", sa.BigInteger(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_immutable_timestamp", "audit_logs_immutable", ["timestamp"])
    op.create_index("ix_audit_immutable_user_id", "audit_logs_immutable", ["user_id"])
    op.create_index("ix_audit_immutable_action", "audit_logs_immutable", ["action"])
    op.create_index("ix_audit_immutable_resource", "audit_logs_immutable", ["resource"])
    op.create_index("ix_audit_immutable_request_id", "audit_logs_immutable", ["request_id"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("ix_doc_versions_doc_id", "document_versions", ["document_id"])
    op.create_index("ix_doc_versions_version", "document_versions", ["version"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("prompt_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_versions_prompt_id", "prompt_versions", ["prompt_id"])
    op.create_index("ix_prompt_versions_active", "prompt_versions", ["prompt_id", "is_active"])


def downgrade():
    op.drop_table("prompt_versions")
    op.drop_table("document_versions")
    op.drop_table("audit_logs_immutable")
