import json
import re

from app.core.logging import get_logger

logger = get_logger(__name__)

LEGAL_KEYWORDS = [
    "bns",
    "bnss",
    "bsa",
    "ipc",
    "crpc",
    "cpc",
    "indian penal code",
    "criminal procedure",
    "bharatiya nyaya sanhita",
    "bharatiya nagarik suraksha sanhita",
    "bharatiya sakshya adhiniyam",
    "section",
    "sec",
    "act",
    "law",
    "legal",
    "court",
    "judge",
    "justice",
    "advocate",
    "lawyer",
    "trial",
    "appeal",
    "petition",
    "suit",
    "plaint",
    "notice",
    "fir",
    "bail",
    "arrest",
    "custody",
    "imprisonment",
    "punishment",
    "penalty",
    "fine",
    "offence",
    "offense",
    "crime",
    "criminal",
    "theft",
    "robbery",
    "murder",
    "assault",
    "fraud",
    "cheating",
    "defamation",
    "divorce",
    "marriage",
    "matrimonial",
    "custody",
    "maintenance",
    "alimony",
    "child support",
    "consumer",
    "complaint",
    "agreement",
    "contract",
    "will",
    "testament",
    "inheritance",
    "property",
    "landlord",
    "tenant",
    "rent",
    "lease",
    "employment",
    "salary",
    "termination",
    "negligence",
    "accident",
    "claim",
    "compensation",
    "damages",
    "injunction",
    "possession",
    "recovery",
    "debt",
    "loan",
    "mortgage",
    "pledge",
    "guarantee",
    "surety",
    "bond",
    "affidavit",
    "declaration",
    "verification",
    "oath",
    "notary",
    "witness",
    "evidence",
    "testimony",
    "summons",
    "warrant",
    "decree",
    "judgment",
    "order",
    "sentence",
    "constitution",
    "fundamental right",
    "writ",
    "habeas corpus",
    "mandamus",
    "certiorari",
    "prohibition",
    "quo warranto",
    "suo moto",
    "locus standi",
    "res judicata",
    "limitation",
    "prescription",
    "statute",
    "code",
    "sanhita",
    "adhiniyam",
    "advocate",
    "counsel",
    "solicitor",
    "bar",
    "bench",
    "tribunal",
    "commission",
    "legal notice",
    "legal heir",
    "legal representative",
    "legal guardian",
    "anticipatory bail",
    "regular bail",
    "default bail",
    "interim bail",
    "charge sheet",
    "investigation",
    "inquiry",
    "cognizance",
    "committal",
    "conviction",
    "acquittal",
    "discharge",
    "release",
    "parole",
    "furlough",
    "probation",
    "suspended sentence",
    "fine",
    "forfeiture",
    "confiscation",
    "dying declaration",
    "circumstantial evidence",
    "direct evidence",
    "documentary evidence",
    "alibi",
    "motive",
    "intention",
    "knowledge",
    "recklessness",
    "negligence",
    "culpable homicide",
    "murder",
    "attempt",
    "abetment",
    "criminal conspiracy",
    "rioting",
    "unlawful assembly",
    "forgery",
    "counterfeit",
    "criminal breach of trust",
    "criminal misappropriation",
    "receiving stolen property",
    "extortion",
    "criminal intimidation",
    "insult",
    "annoyance",
    "trespass",
    "house breaking",
    "larceny",
    "embezzlement",
    "bribery",
    "corruption",
    "criminal misconduct",
    "rape",
    "sexual assault",
    "sexual harassment",
    "dowry death",
    "cruelty",
    "kidnapping",
    "abduction",
    "slavery",
    "bonded labour",
    "human trafficking",
    "hurt",
    "grievous hurt",
    "poisoning",
    "strangulation",
    "drowning",
    "dacoity",
    "robbery",
    "burglary",
    "theft",
    "extortion",
    "criminal force",
    "assault",
    "wrongful restraint",
    "wrongful confinement",
    "criminal trespass",
    "mischief",
    "criminal breach of contract",
    "adultery",
    "bigamy",
    "polygamy",
    "dowry",
    "stridhan",
    "maintenance pendente lite",
    "interim maintenance",
    "guardianship",
    "adoption",
    "succession",
    "probate",
    "letters of administration",
    "patent",
    "copyright",
    "trademark",
    "intellectual property",
    "cyber crime",
    "information technology",
    "data protection",
    "privacy",
    "defamation",
    "contempt of court",
    "perjury",
    "fabrication of evidence",
]

NON_LEGAL_INDICATORS = [
    r"(?i)(how to (cook|make|prepare|bake|fry|boil))",
    r"(?i)(recipe|ingredients|cuisine|dish|food)",
    r"(?i)(father of|mother of|founder of|inventor of|creator of)",
    r"(?i)(what is (software|hardware|coding|programming|computer|mobile|phone|app))",
    r"(?i)(sport|game|cricket|football|hockey|tennis|chess|player|tournament)",
    r"(?i)(movie|film|song|music|actor|actress|singer|director|album)",
    r"(?i)(how old|age of|born|birth|death)",
    r"(?i)(capital of|population of|currency of|language of|flag of)",
    r"(?i)(weather|temperature|climate|rain|forecast)",
    r"(?i)(translate|translator|meaning in (hindi|tamil|telugu|malayalam|kannada))",
    r"(?i)(math|algebra|geometry|calculus|physics|chemistry|biology|science)",
    r"(?i)(python|javascript|java|c\+\+|rust|golang|react|angular|node)",
    r"(?i)(stock|share|market|trading|investment|crypto|bitcoin)",
    r"(?i)(history of|timeline of|overview of|introduction to) (?!.*(law|act|section|court|crime))",
    r"(?i)(dosa|idli|sambar|biryani|pizza|burger|pasta|noodle)",
    r"(?i)(car|bike|vehicle|automobile|engine|repair|maintenance) (?!.*(accident|claim|negligence))",
    r"(?i)(doctor|hospital|disease|symptom|treatment|cure|medicine|surgery) (?!.*(negligence|malpractice|claim))",
]

BNS_TOPICS = [
    "bns",
    "bnss",
    "bsa",
    "bharatiya nyaya sanhita",
    "bharatiya nagarik suraksha sanhita",
    "theft",
    "bail",
    "fir",
    "divorce",
    "consumer",
    "property",
    "labour",
    "cyber",
    "murder",
    "assault",
    "robbery",
    "dacoity",
    "extortion",
    "criminal breach of trust",
    "cheating",
    "forgery",
    "counterfeiting",
    "defamation",
    "criminal intimidation",
    "rape",
    "sexual harassment",
    "dowry",
    "cruelty",
    "kidnapping",
    "abduction",
    "hurt",
    "grievous hurt",
    "wrongful restraint",
    "wrongful confinement",
    "criminal trespass",
    "house breaking",
    "mischief",
    "criminal force",
    "assault",
    "riot",
    "unlawful assembly",
    "abetment",
    "criminal conspiracy",
    "attempt",
    "sedition",
    "waging war",
    "offences against state",
    "offences relating to elections",
    "offences relating to religion",
    "offences relating to marriage",
    "offences relating to documents",
    "offences relating to property",
    "offences relating to public health",
    "offences relating to public safety",
    "offences relating to weights and measures",
    "offences relating to coins and stamps",
    "offences relating to contempt",
    "legal notice",
    "plaint",
    "suit",
    "petition",
    "application",
    "appeal",
    "revision",
    "reference",
    "review",
    "execution",
    "decree",
    "order",
    "summons",
    "warrant",
    "charge sheet",
    "charge",
    "framing of charge",
    "plea",
    "bargaining",
    "compounding",
    "withdrawal",
    "discharge",
    "acquittal",
    "conviction",
    "sentence",
    "fine",
    "imprisonment",
    "death penalty",
    "life imprisonment",
    "probation",
    "parole",
    "anticipatory bail",
    "regular bail",
    "interim bail",
    "default bail",
    "maintenance",
    "alimony",
    "custody",
    "guardianship",
    "adoption",
    "succession",
    "inheritance",
    "will",
    "testament",
    "executor",
    "affidavit",
    "undertaking",
    "surety",
    "bond",
    "guarantee",
    "notice period",
    "termination",
    "resolution",
    "winding up",
    "arbitration",
    "conciliation",
    "mediation",
    "lok adalat",
    "plea bargaining",
    "compounding of offence",
    "withdrawal of case",
    "transfer of case",
    "consolidation of cases",
    "caveat",
    "legal services authority",
    "legal aid",
    "pro bono",
    "affidavit in evidence",
    "examination in chief",
    "cross examination",
    "re-examination",
    "recall of witness",
    "commission for examination",
]


class QueryValidator:
    def __init__(self):
        self._kb_topics = self._load_kb_topics()

    def _load_kb_topics(self) -> set:
        topics = set(BNS_TOPICS)
        kb_path = "data/kb/offline_knowledge_base.json"
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                kb = json.load(f)
            for key in kb:
                topics.add(key.lower().replace("_", " "))
                entry = kb[key]
                if entry.get("title"):
                    topics.add(entry["title"].lower())
                if entry.get("sections"):
                    topics.add(entry["sections"].lower())
        except Exception as e:
            logger.warning("kb_topic_load_failed", error=str(e))
        return topics

    def is_legal_query(self, query: str) -> tuple[bool, float, str]:
        q = query.lower().strip()
        q_words = len(q.split())

        for indicator in NON_LEGAL_INDICATORS:
            if re.search(indicator, q):
                matched = re.search(indicator, q).group()
                return False, 0.0, f"Query appears non-legal: '{matched[:60]}'"

        keyword_score = 0
        matched_keywords = []
        for kw in LEGAL_KEYWORDS:
            if kw in q:
                keyword_score += 1
                matched_keywords.append(kw)
                if len(matched_keywords) >= 5:
                    break

        topic_score = 0
        matched_topics = []
        for topic in self._kb_topics:
            if topic in q:
                topic_score += 1
                matched_topics.append(topic)
                if len(matched_topics) >= 3:
                    break

        section_refs = re.findall(r"(?i)(?:section|sec\.?)\s+\d+", q)
        section_score = len(section_refs) * 5

        total_score = keyword_score + topic_score * 3 + section_score

        about_self = re.match(
            r"(?i)^(who are you|what are you|what is this|tell me about yourself|introduce yourself)\s*", q
        )
        if about_self:
            return True, 0.9, "Greeting / about-self query"

        greeting = re.match(r"(?i)^(hi|hello|hey|namaste|namaskar)\s*", q)
        if greeting:
            return True, 0.5, "Greeting detected"

        if section_refs:
            return True, min(0.95, 0.5 + section_score * 0.05), "Section reference detected"

        if topic_score > 0:
            confidence = min(0.95, total_score / (max(q_words, 1)) * 0.3)
            return True, round(confidence, 2), "BNS/Indian law query detected"

        if keyword_score >= 1 and total_score > 1 and q_words >= 2:
            confidence = min(0.85, total_score / (max(q_words, 1)) * 0.25)
            return True, round(confidence, 2), f"Legal query detected via keywords: {', '.join(matched_keywords[:3])}"

        if q_words == 1 and keyword_score >= 1:
            return True, 0.5, f"Single legal keyword: {matched_keywords[0]}"

        return False, 0.0, "Query is not related to BNS/Indian law"

    def get_rejection_message(self, query: str) -> str:
        return (
            f"I specialize exclusively in the **Bharatiya Nyaya Sanhita (BNS)**, "
            f"**Bharatiya Nagarik Suraksha Sanhita (BNSS)**, and related Indian criminal law. "
            f"Your query about '{query[:80]}...' does not appear to be related to Indian "
            f"criminal law or the BNS framework.\n\n"
            f"Please ask a question about:\n"
            f"- BNS sections and punishments\n"
            f"- Criminal procedure (FIR, bail, arrest, trial)\n"
            f"- Legal document drafting (bail application, FIR, legal notice, affidavit)\n"
            f"- Court procedures and legal rights\n"
            f"- Comparison of legal provisions\n\n"
            f"*This is an AI legal information system and not a general-purpose assistant.*"
        )

    def get_greeting_response(self) -> str:
        return (
            "Hello! I am **BNS AI**, your specialized assistant for the **Bharatiya Nyaya Sanhita (BNS)** "
            "and Indian criminal law.\n\n"
            "I can help you with:\n"
            '- **BNS Section Lookup** — Ask about any section, e.g., "What is Section 302 BNS?"\n'
            "- **Legal Guidance** — Ask about criminal procedure, bail, FIR, trial process\n"
            "- **Document Drafting** — Generate FIR, bail applications, legal notices, affidavits\n"
            "- **Rights Advisory** — Know your legal rights in criminal matters\n"
            "- **Legal Comparison** — Compare legal concepts and provisions\n\n"
            "How can I assist you with Indian criminal law today?"
        )


query_validator = QueryValidator()
