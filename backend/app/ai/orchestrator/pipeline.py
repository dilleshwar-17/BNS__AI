import time
import uuid

from app.ai.llms.router import direct_kb_response, generate_fallback_response, llm_router
from app.ai.orchestrator.intent_classifier import IntentClassifier
from app.ai.validators.output_validator import classify_query, expand_query
from app.ai.validators.query_validator import query_validator
from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

MODE_SYSTEM_PROMPTS = {
    "legal_guidance": (
        "You are BNS AI, a legal information assistant specialized in Indian criminal law.\n\n"
        "Provide clear, structured legal guidance. Use this format:\n"
        "## Direct Answer\n[Direct answer to the question]\n\n"
        "## Explanation\n[Detailed explanation]\n\n"
        "## Relevant Sections\n[List applicable BNS/BNSS/BSA sections]\n\n"
        "## Key Points\n[Bullet list of important points]\n\n"
        "Base your answer on the retrieved legal context below. If the context doesn't contain "
        "enough information, say so clearly. Never fabricate sections or punishments."
    ),
    "section_lookup": (
        "You are BNS AI, specialized in BNS section lookup.\n\n"
        "Provide the full text of the requested section, its classification (bailable/cognizable/etc.), "
        "punishment if any, and a plain-language explanation.\n\n"
        "Use this format:\n"
        "## Section [number]\n[Full text of the section]\n\n"
        "## Classification\n[Bailable/Non-bailable, Cognizable/Non-cognizable, etc.]\n\n"
        "## Punishment\n[If applicable]\n\n"
        "## Plain English Explanation\n[Simple explanation]\n\n"
        "Only use information from the retrieved context. Do not invent section content."
    ),
    "legal_procedure": (
        "You are BNS AI, specialized in Indian criminal procedure.\n\n"
        "Provide step-by-step procedural guidance. Cover:\n"
        "- Who can file/apply\n"
        "- Where to file\n"
        "- Documents required\n"
        "- Timeline\n"
        "- Relevant forms\n"
        "- Expected outcome\n\n"
        "Use information from the retrieved context. Indicate if you're unsure about any step."
    ),
    "rights_advisory": (
        "You are BNS AI, specialized in legal rights under Indian criminal law.\n\n"
        "Explain the relevant legal rights clearly and practically. Cover:\n"
        "- What the right is\n"
        "- Which law guarantees it\n"
        "- How to exercise it\n"
        "- What to do if violated\n\n"
        "Ground all information in the retrieved context. Never speculate about rights."
    ),
    "case_law": (
        "You are BNS AI, specialized in Indian criminal case law.\n\n"
        "When discussing case law, provide:\n"
        "- Case name and citation\n"
        "- Court and year\n"
        "- Facts briefly\n"
        "- Legal issue\n"
        "- Ratio decidendi\n"
        "- Current relevance\n\n"
        "Only cite cases present in the retrieved context. Do not fabricate judgments."
    ),
    "comparison": (
        "You are BNS AI, specialized in comparing legal concepts.\n\n"
        "Provide a balanced comparison covering:\n"
        "- Definitions of each concept\n"
        "- Key differences\n"
        "- Similarities if any\n"
        "- Practical implications\n"
        "- Relevant sections for each\n\n"
        "Use a table format for differences where helpful. Base comparisons on retrieved context."
    ),
    "deep_research": (
        "You are BNS AI, specialized in comprehensive legal research.\n\n"
        "Provide a thorough analysis covering:\n"
        "- Overview and scope\n"
        "- Historical context\n"
        "- Key provisions with section numbers\n"
        "- Judicial interpretation\n"
        "- Practical application\n"
        "- Related concepts\n"
        "- Statistical or procedural data if available\n\n"
        "Organize with clear headings. Be comprehensive but accurate."
    ),
    "legal_drafting": (
        "You are BNS AI, specialized in legal document drafting.\n\n"
        "Guide the user through the drafting process. Provide:\n"
        "- Document structure\n"
        "- Required parties and details\n"
        "- Key clauses and their purpose\n"
        "- Legal requirements for validity\n"
        "- Registration or notarization needs if applicable\n\n"
        "For actual document generation, use the dedicated drafting service."
    ),
}

DEFAULT_PROMPT = MODE_SYSTEM_PROMPTS["legal_guidance"]

MODE_DESCRIPTIONS = {
    "legal_guidance": "Get legal guidance on BNS and Indian criminal law",
    "section_lookup": "Look up specific BNS/BNSS/BSA sections",
    "legal_procedure": "Learn about criminal procedures and processes",
    "rights_advisory": "Know your legal rights in criminal matters",
    "case_law": "Research case law and precedents",
    "comparison": "Compare legal concepts and provisions",
    "deep_research": "Get in-depth analysis of legal topics",
    "legal_drafting": "Draft legal documents step by step",
}


class AIOrchestrator:
    def __init__(self):
        self.classifier = IntentClassifier()
        self.metrics = {"total_pipelines": 0, "total_elapsed": 0.0, "by_mode": {}}

    async def process(
        self, query: str, mode: str = "legal_guidance", user_id: str | None = None, chat_history: list | None = None
    ) -> dict:
        pipeline_id = str(uuid.uuid4())
        start_time = time.time()
        self.metrics["total_pipelines"] += 1

        logger.info("pipeline_started", pipeline_id=pipeline_id, mode=mode, query=query[:80], user=user_id)

        steps = {}
        result = {
            "pipeline_id": pipeline_id,
            "query": query,
            "mode": mode,
            "response": "",
            "sources": [],
            "confidence": 0.0,
            "steps": steps,
            "elapsed_seconds": 0,
            "error": None,
        }

        # Step 1: Validate query
        try:
            s1 = time.time()
            steps["validation"] = self._validate(query)
            steps["validation"]["elapsed"] = round(time.time() - s1, 3)

            if steps["validation"]["rejected"]:
                result["response"] = steps["validation"]["response"]
                result["confidence"] = steps["validation"]["confidence"]
                result["elapsed_seconds"] = round(time.time() - start_time, 3)
                return result
        except Exception as e:
            logger.error("validation_failed", error=str(e))
            result["error"] = f"Validation failed: {str(e)}"
            result["elapsed_seconds"] = round(time.time() - start_time, 3)
            return result

        # Step 2: Classify intent
        try:
            s2 = time.time()
            intent = await self.classifier.classify(query)
            intent["mode"] = mode
            steps["classification"] = intent
            steps["classification"]["elapsed"] = round(time.time() - s2, 3)
        except Exception as e:
            logger.warning("classification_failed", error=str(e))
            steps["classification"] = {"intent": "legal_guidance", "mode": mode, "error": str(e)}

        # Step 3: Retrieve context
        try:
            s3 = time.time()
            retrieval = await self._retrieve(query, mode)
            steps["retrieval"] = retrieval
            steps["retrieval"]["elapsed"] = round(time.time() - s3, 3)
        except Exception as e:
            logger.warning("retrieval_failed", error=str(e))
            steps["retrieval"] = {"context": "", "results": [], "error": str(e)}

        # Step 4: Build prompt
        try:
            s4 = time.time()
            prompt_data = self._build_prompt(query, mode, steps["retrieval"].get("context", ""), chat_history)
            steps["prompt"] = prompt_data
            steps["prompt"]["elapsed"] = round(time.time() - s4, 3)
        except Exception as e:
            logger.warning("prompt_build_failed", error=str(e))
            steps["prompt"] = {"error": str(e), "system_prompt": MODE_SYSTEM_PROMPTS.get(mode, DEFAULT_PROMPT)}

        # Step 5: Generate response
        try:
            s5 = time.time()
            response = await self._generate(prompt_data.get("full_prompt", query), mode)
            steps["generation"] = response
            steps["generation"]["elapsed"] = round(time.time() - s5, 3)
            result["response"] = response.get("text", "")
            result["provider"] = response.get("provider", "unknown")
        except Exception as e:
            logger.error("generation_failed", error=str(e))
            result["response"] = generate_fallback_response(query)
            steps["generation"] = {"error": str(e), "fallback": True}

        # Step 6: Post-process
        try:
            s6 = time.time()
            result["response"] = self._post_process(result["response"], query)
            steps["post_processing"] = {"elapsed": round(time.time() - s6, 3)}
        except Exception as e:
            logger.warning("post_process_failed", error=str(e))

        # Build sources list
        sources = []
        for r in steps.get("retrieval", {}).get("results", []):
            src = {
                "id": r.get("id", ""),
                "source": r.get("source", ""),
                "score": r.get("score", 0),
                "text_preview": r.get("text", "")[:150],
            }
            if src["id"] and src["id"] not in {s["id"] for s in sources}:
                sources.append(src)
        result["sources"] = sources[:10]
        result["confidence"] = steps.get("validation", {}).get("confidence", 0.5)
        result["elapsed_seconds"] = round(time.time() - start_time, 3)

        # Update metrics
        self.metrics["total_elapsed"] += result["elapsed_seconds"]
        if mode not in self.metrics["by_mode"]:
            self.metrics["by_mode"][mode] = {"count": 0, "total_elapsed": 0.0}
        self.metrics["by_mode"][mode]["count"] += 1
        self.metrics["by_mode"][mode]["total_elapsed"] += result["elapsed_seconds"]

        elapsed = result["elapsed_seconds"]
        logger.info(
            "pipeline_completed",
            pipeline_id=pipeline_id,
            elapsed=elapsed,
            mode=mode,
            response_len=len(result["response"]),
        )

        return result

    def _validate(self, query: str) -> dict:
        is_legal, confidence, reason = query_validator.is_legal_query(query)

        if not is_legal:
            return {
                "rejected": True,
                "confidence": confidence,
                "reason": reason,
                "response": query_validator.get_rejection_message(query),
            }

        greeting = query.lower().strip() in ["hi", "hello", "hey", "namaste", "namaskar"]
        if greeting:
            return {
                "rejected": True,
                "confidence": 0.9,
                "reason": "greeting",
                "response": query_validator.get_greeting_response(),
            }

        return {
            "rejected": False,
            "confidence": confidence,
            "reason": reason,
            "response": None,
        }

    async def _retrieve(self, query: str, mode: str) -> dict:
        context = ""
        results = []
        strategies_used = []
        breakdown = {}

        try:
            from app.ai.retrieval.hybrid_search import RetrievalPipeline

            pipeline = RetrievalPipeline()
            classified_type = classify_query(query)
            expanded = expand_query(query, classified_type)

            retrieval_result = await pipeline.retrieve(
                query=query,
                query_info={"type": classified_type, "sections": expanded.get("sections", [])},
                top_k=8,
            )

            context = retrieval_result.get("context", "")
            results = retrieval_result.get("results", [])
            breakdown = retrieval_result.get("breakdown", {})
            strategies_used = [k for k, v in breakdown.items() if v > 0]
        except Exception as e:
            logger.warning("hybrid_retrieval_failed", error=str(e))

        if not context:
            kb_text = llm_router._get_kb_context(query)
            if kb_text:
                context = kb_text
                strategies_used.append("offline_kb")

        return {
            "context": context,
            "results": results,
            "strategies_used": strategies_used,
            "breakdown": breakdown,
            "total_results": len(results),
        }

    def _build_prompt(self, query: str, mode: str, context: str, chat_history: list | None = None) -> dict:
        system_prompt = MODE_SYSTEM_PROMPTS.get(mode, DEFAULT_PROMPT)

        if context:
            system_prompt += (
                f"\n\n## Retrieved Legal Context\n"
                f"The following information was retrieved from the legal knowledge base. "
                f"Use it to ground your answer. If the context is not directly relevant, "
                f"say so.\n\n{context}\n"
            )

        system_prompt += (
            "\n\n## Response Rules\n"
            "- Answer in plain English with clear structure\n"
            "- Cite specific BNS/BNSS/BSA sections from the context\n"
            "- If the context lacks information, say: 'The available legal sources do not "
            "contain specific information on this point.'\n"
            "- Never fabricate sections, punishments, or citations\n"
            "- End with: *This is general legal information. Consult a qualified lawyer for specific advice.*\n"
        )

        full_prompt = f"{system_prompt}\n\nUser query: {query}"

        return {
            "system_prompt": system_prompt,
            "full_prompt": full_prompt,
            "mode": mode,
            "estimated_tokens": len(full_prompt) // 4,
        }

    async def _generate(self, prompt: str, mode: str) -> dict:
        kb_result = direct_kb_response(prompt)
        if kb_result:
            return {"text": kb_result, "provider": "offline_kb", "from_cache": True}

        try:
            text = await llm_router.route(prompt, mode)
            if text and len(text) > 10:
                return {"text": text, "provider": "llm", "from_cache": False}
        except Exception as e:
            logger.warning("llm_generation_failed", error=str(e))

        kb_result = direct_kb_response(prompt)
        if kb_result:
            return {"text": kb_result, "provider": "offline_kb_fallback", "from_cache": True}

        return {"text": generate_fallback_response(prompt), "provider": "fallback", "from_cache": False}

    def _post_process(self, response: str, original_query: str) -> str:
        if not response or len(response) < 10:
            return response

        import re

        response = re.sub(
            r"(?i)(IPC Section|Indian Penal Code|Section\s+\d+\s+IPC)",
            lambda m: m.group().replace("IPC", "BNS").replace("Indian Penal Code", "BNS (Bharatiya Nyaya Sanhita)"),
            response,
        )
        response = re.sub(
            r"(?i)(CrPC|Code of Criminal Procedure)",
            lambda m: m.group()
            .replace("CrPC", "BNSS")
            .replace("Code of Criminal Procedure", "BNSS (Bharatiya Nagarik Suraksha Sanhita)"),
            response,
        )
        response = re.sub(
            r"(?i)(Indian Evidence Act|Evidence Act)",
            lambda m: m.group()
            .replace("Indian Evidence Act", "BSA (Bharatiya Sakshya Adhiniyam)")
            .replace("Evidence Act", "BSA"),
            response,
        )

        return response

    def get_metrics(self) -> dict:
        m = dict(self.metrics)
        if m["total_pipelines"] > 0:
            m["avg_elapsed"] = round(m["total_elapsed"] / m["total_pipelines"], 3)
        return m

    def get_status(self) -> dict:
        return {
            "status": "operational",
            "total_processed": self.metrics["total_pipelines"],
            "modes_supported": list(MODE_SYSTEM_PROMPTS.keys()),
            "metrics": self.get_metrics(),
        }


pipeline = AIOrchestrator()
