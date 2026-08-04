"""SQLAlchemy models (grouped by domain).

Importing models here ensures their tables are registered on the declarative
base metadata before Alembic autogeneration / introspection. Order matters for
relationship discovery.
"""

from app.models.analysis import DocumentAnalysis
from app.models.audit import AuditEvent
from app.models.auth_sessions import AuthSession
from app.models.case import (
    AlternativeScenario,
    CandidateProvision,
    Case,
    CaseContradiction,
    CaseEvidence,
    CaseFact,
    CaseFollowUp,
    CaseMember,
    CaseMissingFact,
    CaseParty,
    CaseTimelineEvent,
    CaseVersion,
    ElementOfOffence,
    OutcomeScenario,
)
from app.models.chat import Conversation, Message, MessageCitation
from app.models.chunks import DocumentChunk
from app.models.memory import ConversationMemory
from app.models.pleading import CasePleading
from app.models.rbac import Permission, Role, role_permissions, user_roles
from app.models.report import CaseReport
from app.models.research import ResearchReport, ResearchRun, ResearchSession
from app.models.sources import IngestionJob, LegalSource, SourceDocument, SourceVersion
from app.models.user import User

__all__ = [
    "AuditEvent",
    "User",
    "AuthSession",
    "Role",
    "Permission",
    "user_roles",
    "role_permissions",
    "LegalSource",
    "SourceVersion",
    "SourceDocument",
    "IngestionJob",
    "DocumentChunk",
    "Conversation",
    "Message",
    "MessageCitation",
    "ConversationMemory",
    "DocumentAnalysis",
    "ResearchSession",
    "ResearchRun",
    "ResearchReport",
    "Case",
    "CaseMember",
    "CaseParty",
    "CaseFact",
    "CaseEvidence",
    "CaseTimelineEvent",
    "CaseContradiction",
    "CaseMissingFact",
    "CandidateProvision",
    "ElementOfOffence",
    "AlternativeScenario",
    "OutcomeScenario",
    "CaseFollowUp",
    "CaseVersion",
    "CasePleading",
    "CaseReport",
]
