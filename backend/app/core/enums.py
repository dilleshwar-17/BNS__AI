from enum import Enum


class ChatMode(str, Enum):
    LEGAL_GUIDANCE = "legal_guidance"
    LEGAL_DRAFTING = "legal_drafting"
    SECTION_LOOKUP = "section_lookup"
    LEGAL_PROCEDURE = "legal_procedure"
    RIGHTS_ADVISORY = "rights_advisory"
    CASE_LAW = "case_law"
    COMPARISON = "comparison"
    DEEP_RESEARCH = "deep_research"
    DOCUMENT_ANALYSIS = "document_analysis"


class DocumentType(str, Enum):
    FIR = "fir"
    LEGAL_NOTICE = "legal_notice"
    BAIL_APPLICATION = "bail_application"
    AFFIDAVIT = "affidavit"
    CONSUMER_COMPLAINT = "consumer_complaint"
    AGREEMENT = "agreement"
    CIVIL_PLAINT = "civil_plaint"
    DIVORCE_PETITION = "divorce_petition"
    WILL = "will"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class RetrievalStrategy(str, Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    GRAPH = "graph"
    HYBRID = "hybrid"
    DECOMPOSE = "decompose"
