"""Create document chunks table (Phase 4).

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_version_id", sa.Uuid(), sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_chunk_id", sa.Uuid(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("chapter_id", sa.String(length=30), nullable=True),
        sa.Column("chapter_title", sa.String(length=300), nullable=True),
        sa.Column("section_id", sa.String(length=30), nullable=True),
        sa.Column("section_title", sa.String(length=400), nullable=True),
        sa.Column("subsection", sa.String(length=30), nullable=True),
        sa.Column("element_type", sa.String(length=30), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("page_numbers", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_source_version_id", "document_chunks", ["source_version_id"])
    op.create_index("ix_document_chunks_parent_chunk_id", "document_chunks", ["parent_chunk_id"])
    op.create_index("ix_document_chunks_chapter_id", "document_chunks", ["chapter_id"])
    op.create_index("ix_document_chunks_section_id", "document_chunks", ["section_id"])
    op.create_index("ix_document_chunks_content_hash", "document_chunks", ["content_hash"])
    op.create_index("ix_document_chunks_src_section", "document_chunks", ["source_version_id", "section_id"])
    op.create_index("ix_document_chunks_src_elem", "document_chunks", ["source_version_id", "element_type"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_src_elem", table_name="document_chunks")
    op.drop_index("ix_document_chunks_src_section", table_name="document_chunks")
    op.drop_index("ix_document_chunks_content_hash", table_name="document_chunks")
    op.drop_index("ix_document_chunks_section_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_chapter_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_parent_chunk_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_source_version_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
