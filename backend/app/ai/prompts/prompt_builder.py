from app.ai.agents.base_agent import BaseAgent
from app.ai.examples.loader import get_few_shot_loader
from app.ai.orchestrator.workflow_router import Message
from app.ai.prompts.system import SYSTEM_PROMPT
from app.core.logging import get_logger

logger = get_logger(__name__)

WORKFLOW_PROMPTS = {
    "legal_guidance": f"""{SYSTEM_PROMPT}

## Workflow: Legal Guidance
Explain Indian law to the user. Answer first, then explain.

Structure your response as:
## Direct Answer (1-2 sentences)
## Applicable Law (Act, Section)
## Explanation (plain language)
## Punishment (if applicable)
## Procedure (if applicable)
## Example

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "legal_drafting": f"""{SYSTEM_PROMPT}

## Workflow: Legal Drafting
Do NOT draft yet. Ask for required information first.
Collect details: parties, dates, facts, relief sought.
Only draft after all mandatory fields filled.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "section_lookup": f"""{SYSTEM_PROMPT}

## Workflow: Section Lookup
Return: Section Number, Section Title, Meaning, Punishment, Example.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "legal_procedure": f"""{SYSTEM_PROMPT}

## Workflow: Legal Procedure
Explain the legal process step by step with applicable sections and timelines.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "rights_advisory": f"""{SYSTEM_PROMPT}

## Workflow: Rights Advisory
Explain the legal rights involved, legal basis, and how to enforce them.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "case_law": f"""{SYSTEM_PROMPT}

## Workflow: Case Law
Discuss relevant judgments. Only cite verified cases.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "comparison": f"""{SYSTEM_PROMPT}

## Workflow: Comparison
Compare legal concepts. Use tables for differences.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "deep_research": f"""{SYSTEM_PROMPT}

## Workflow: Deep Research
Provide comprehensive legal analysis with citations.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "document_analysis": f"""{SYSTEM_PROMPT}

## Workflow: Document Analysis
Analyze the document. Summarize key clauses, risks, obligations.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
    "default": f"""{SYSTEM_PROMPT}

Answer the legal question with section references where applicable.

Retrieved Legal Context:
{{context}}

User Query: {{query}}
""",
}


class PromptBuilderAgent(BaseAgent):
    def __init__(self):
        super().__init__("prompt_builder", "Dynamically builds prompts with context injection")
        self.subscribe_to("build_prompt")

    async def process(self, message: Message) -> dict:
        return self.build(message.payload)

    def build(self, payload: dict) -> dict:
        query = payload.get("query", "")
        context = payload.get("context", "")
        classification = payload.get("classification", {})
        user_id = payload.get("user_id")

        qtype = classification.get("primary_type", "default")
        template = WORKFLOW_PROMPTS.get(qtype, WORKFLOW_PROMPTS["default"])

        complexity = classification.get("complexity", "medium")
        sections = classification.get("sections", [])
        topics = classification.get("topics", [])

        context_parts = []
        if context:
            context_parts.append(context)

        if sections:
            section_text = f"Relevant BNS Sections: {', '.join(f'Section {s}' for s in sections)}"
            context_parts.append(section_text)

        if topics:
            topic_text = f"Legal Topics: {', '.join(topics)}"
            context_parts.append(topic_text)

        if classification.get("confidence", 1) < 0.4:
            context_parts.append(
                "Note: Query classification confidence is low. Verify the legal area matches the user's intent."
            )

        try:
            loader = get_few_shot_loader()
            examples = loader.get_examples(
                query_type=qtype,
                sections=[int(s) for s in sections if str(s).isdigit()],
                max_examples=2,
            )
            if examples:
                context_parts.append(loader.format_examples(examples))
        except Exception as e:
            logger.warning("few_shot_injection_failed", error=str(e))

        full_context = "\n\n".join(context_parts) if context_parts else "General legal knowledge base."

        prompt = template.format(query=query, context=full_context)

        if complexity == "easy":
            prompt += "\n\nProvide a simple, clear answer suitable for a non-legal audience."
        elif complexity == "hard":
            prompt += "\n\nProvide a detailed, comprehensive analysis suitable for legal professionals."

        if user_id:
            profile = self.get_user_profile(user_id)
            pref_mode = profile.get_preferred_mode()
            if pref_mode != qtype:
                prompt += f"\n\nNote: User typically prefers {pref_mode} mode responses."

        token_estimate = len(prompt.split()) * 1.3
        self.log(
            "built",
            query_type=qtype,
            complexity=complexity,
            context_chars=len(full_context),
            estimated_tokens=int(token_estimate),
        )

        return {
            "prompt": prompt,
            "template_used": qtype,
            "context_size": len(full_context),
            "estimated_tokens": int(token_estimate),
            "sections_injected": sections,
            "topics_injected": topics,
        }


prompt_builder = PromptBuilderAgent()
