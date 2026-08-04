"""Create case intelligence tables (Phase 18).

Revision ID: 0009
Revises: 0008

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pk(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
        autoincrement=True,
        nullable=False,
    )


def _fk_int(column: str, table: str, ondelete: str = "CASCADE") -> sa.Column:
    return sa.Column(
        column,
        sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
        sa.ForeignKey(f"{table}.id", ondelete=ondelete),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "cases",
        _pk("id"),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("matter_number", sa.String(length=100), nullable=True),
        sa.Column("court", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_cases"),
    )
    op.create_index("ix_cases_owner_id", "cases", ["owner_id"])

    op.create_table(
        "case_members",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_in_case", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_members"),
    )
    op.create_index("ix_case_members_case_id", "case_members", ["case_id"])
    op.create_index("ix_case_members_user_id", "case_members", ["user_id"])

    op.create_table(
        "case_parties",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("side", sa.String(length=30), nullable=True),
        sa.Column("is_claimant", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_parties"),
    )
    op.create_index("ix_case_parties_case_id", "case_parties", ["case_id"])

    op.create_table(
        "case_facts",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("provenance", sa.String(length=300), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_facts"),
    )
    op.create_index("ix_case_facts_case_id", "case_facts", ["case_id"])

    op.create_table(
        "case_evidence",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_evidence"),
    )
    op.create_index("ix_case_evidence_case_id", "case_evidence", ["case_id"])

    op.create_table(
        "case_timeline_events",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("when", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_timeline_events"),
    )
    op.create_index("ix_case_timeline_events_case_id", "case_timeline_events", ["case_id"])

    op.create_table(
        "case_contradictions",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column(
            "fact_a_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("case_facts.id"),
            nullable=True,
        ),
        sa.Column(
            "fact_b_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("case_facts.id"),
            nullable=True,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_contradictions"),
    )
    op.create_index("ix_case_contradictions_case_id", "case_contradictions", ["case_id"])

    op.create_table(
        "case_missing_facts",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("what", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_missing_facts"),
    )
    op.create_index("ix_case_missing_facts_case_id", "case_missing_facts", ["case_id"])

    op.create_table(
        "candidate_provisions",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("section_id", sa.String(length=30), nullable=True),
        sa.Column("source_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_provisions"),
    )
    op.create_index("ix_candidate_provisions_case_id", "candidate_provisions", ["case_id"])

    op.create_table(
        "element_of_offence",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("section_id", sa.String(length=30), nullable=True),
        sa.Column("element", sa.String(length=200), nullable=False),
        sa.Column("satisfied", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_element_of_offence"),
    )
    op.create_index("ix_element_of_offence_case_id", "element_of_offence", ["case_id"])

    op.create_table(
        "alternative_scenarios",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_alternative_scenarios"),
    )
    op.create_index("ix_alternative_scenarios_case_id", "alternative_scenarios", ["case_id"])

    op.create_table(
        "outcome_scenarios",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("likelihood", sa.String(length=30), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_outcome_scenarios"),
    )
    op.create_index("ix_outcome_scenarios_case_id", "outcome_scenarios", ["case_id"])

    op.create_table(
        "case_follow_ups",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("due", sa.DateTime(timezone=True), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_follow_ups"),
    )
    op.create_index("ix_case_follow_ups_case_id", "case_follow_ups", ["case_id"])

    op.create_table(
        "case_versions",
        _pk("id"),
        _fk_int("case_id", "cases"),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_case_versions"),
    )
    op.create_index("ix_case_versions_case_id", "case_versions", ["case_id"])


def downgrade() -> None:
    for table, index in [
        ("case_versions", "ix_case_versions_case_id"),
        ("case_follow_ups", "ix_case_follow_ups_case_id"),
        ("outcome_scenarios", "ix_outcome_scenarios_case_id"),
        ("alternative_scenarios", "ix_alternative_scenarios_case_id"),
        ("element_of_offence", "ix_element_of_offence_case_id"),
        ("candidate_provisions", "ix_candidate_provisions_case_id"),
        ("case_missing_facts", "ix_case_missing_facts_case_id"),
        ("case_contradictions", "ix_case_contradictions_case_id"),
        ("case_timeline_events", "ix_case_timeline_events_case_id"),
        ("case_evidence", "ix_case_evidence_case_id"),
        ("case_facts", "ix_case_facts_case_id"),
        ("case_parties", "ix_case_parties_case_id"),
        ("case_members", "ix_case_members_case_id"),
        ("cases", "ix_cases_owner_id"),
    ]:
        op.drop_index(index, table_name=table)
        op.drop_table(table)
