import random
import time
from typing import AsyncIterator, Optional

import httpx

from app.ai.examples.loader import get_few_shot_loader
from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

GEMINI_TRAFFIC_PERCENT = 0.055

DELIMITER_START = "<|user_message|>"
DELIMITER_END = "<|/user_message|>"

REQUEST_TIMEOUT = 60.0
HEALTH_CHECK_INTERVAL = 60.0

SKIP_VALIDATION_MODES = {
    "legal_drafting",
    "document_analysis",
    "legal_analysis",
    "case_strategy",
    "compliance",
    "precedent_search",
}


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_time: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning("circuit_breaker_opened", failures=self.failure_count)

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open" and self.last_failure_time:
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = "half-open"
                return True
        return False


class LLMRouter:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._health: dict[str, bool] = {"ollama": True, "gemini": True, "vector": True, "graph": True, "offline": True}
        self._latency: dict[str, list[float]] = {"ollama": [], "gemini": []}
        self._circuit_breakers: dict[str, CircuitBreaker] = {
            "ollama": CircuitBreaker(),
            "gemini": CircuitBreaker(),
        }
        self._last_health_check = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT))
        return self._client

    async def health_check(self):
        if time.time() - self._last_health_check < HEALTH_CHECK_INTERVAL:
            return
        self._last_health_check = time.time()
        try:
            from app.ingestion.chroma.vector_store import is_healthy

            self._health["vector"] = is_healthy()
        except Exception:
            self._health["vector"] = False

        try:
            client = await self._get_client()
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            self._health["ollama"] = r.status_code == 200
        except Exception:
            self._health["ollama"] = False

        self._health["graph"] = True
        self._health["offline"] = True

    def _get_provider_order(self) -> list[str]:
        providers = []
        if self._health.get("ollama") and self._circuit_breakers["ollama"].can_execute():
            providers.append("ollama")
        if self._health.get("gemini") and self._circuit_breakers["gemini"].can_execute():
            providers.append("gemini")
        providers.extend(["vector", "graph", "offline"])
        return providers

    def _get_mode_routing(self, mode: str) -> list[str]:
        mode_routes = {
            "general": ["ollama", "gemini", "vector", "graph", "offline"],
            "research": ["ollama", "gemini", "vector", "graph", "offline"],
            "legal_analysis": ["ollama", "gemini", "vector", "graph", "offline"],
            "legal_drafting": ["ollama", "gemini"],
            "document_analysis": ["ollama", "vector", "graph", "offline"],
            "case_strategy": ["ollama", "vector", "graph", "offline"],
            "compliance": ["ollama", "vector", "graph", "offline"],
            "precedent_search": ["vector", "graph", "ollama", "offline"],
            "quick_query": ["ollama", "gemini", "vector", "offline"],
        }
        return mode_routes.get(mode, self._get_provider_order())

    def _mix_gemini_traffic(self, providers: list[str]) -> list[str]:
        if "ollama" not in providers or "gemini" not in providers:
            return providers
        if not self._health.get("gemini"):
            return providers
        if not self._circuit_breakers["gemini"].can_execute():
            return providers
        if random.random() < GEMINI_TRAFFIC_PERCENT:
            logger.info("gemini_priority_route", percent=GEMINI_TRAFFIC_PERCENT)
            return ["gemini"] + [p for p in providers if p != "gemini"]
        return providers

    def _get_system_prompt(self, mode: str) -> str:
        from app.ai.prompts.system import SYSTEM_PROMPT

        return SYSTEM_PROMPT

    async def route(self, prompt: str, mode: str = "general", **kwargs) -> str:
        await self.health_check()

        sanitized = self._sanitize_user_input(prompt)

        from app.ai.validators.query_validator import query_validator

        if mode not in SKIP_VALIDATION_MODES:
            is_legal, confidence, reason = query_validator.is_legal_query(sanitized)
            if not is_legal:
                logger.info("query_rejected", reason=reason, confidence=confidence)
                return query_validator.get_rejection_message(sanitized)
            if confidence < 0.6 and is_legal:
                pass

        greeting = sanitized.lower().strip() in ["hi", "hello", "hey", "namaste", "namaskar"]
        if greeting and mode not in SKIP_VALIDATION_MODES:
            logger.info("greeting_detected")
            return query_validator.get_greeting_response()

        kb_context = self._get_kb_context(sanitized)

        system_prompt = self._get_system_prompt(mode)
        if kb_context:
            system_prompt = (
                system_prompt
                + f"\n\n## Retrieved Legal Context\n{kb_context}\n\nUse this context to inform your answer, but prioritize the user's specific query."
            )

        delimited_prompt = self._wrap_with_delimiters(sanitized)
        providers = self._mix_gemini_traffic(self._get_mode_routing(mode))
        last_error = None

        for provider in providers:
            try:
                if provider == "ollama":
                    result = await self._route_ollama(system_prompt, delimited_prompt, **kwargs)
                    self._circuit_breakers["ollama"].record_success()
                    return self._post_process_output(result, sanitized)
                elif provider == "gemini":
                    result = await self._route_gemini(system_prompt, delimited_prompt, **kwargs)
                    self._circuit_breakers["gemini"].record_success()
                    return self._post_process_output(result, sanitized)
                elif provider == "vector":
                    result = await self._route_vector(sanitized)
                    if result and len(result) > 50:
                        return result
                elif provider == "graph":
                    result = await self._route_graph(sanitized)
                    if result:
                        return result
                elif provider == "offline":
                    return self._route_offline(sanitized)
            except Exception as e:
                last_error = e
                if provider in self._circuit_breakers:
                    self._circuit_breakers[provider].record_failure()
                logger.warning("provider_failed", provider=provider, error=str(e))

        logger.error("all_providers_failed", last_error=str(last_error))
        return "I apologize, but I'm unable to process your request at the moment. Please try again later."

    async def stream(self, prompt: str, mode: str = "general", **kwargs) -> AsyncIterator[str]:
        await self.health_check()

        sanitized = self._sanitize_user_input(prompt)

        from app.ai.validators.query_validator import query_validator

        if mode not in SKIP_VALIDATION_MODES:
            is_legal, confidence, reason = query_validator.is_legal_query(sanitized)
            if not is_legal:
                yield query_validator.get_rejection_message(sanitized)
                return

        greeting = sanitized.lower().strip() in ["hi", "hello", "hey", "namaste", "namaskar"]
        if greeting and mode not in SKIP_VALIDATION_MODES:
            yield query_validator.get_greeting_response()
            return

        kb_context = self._get_kb_context(sanitized)
        system_prompt = self._get_system_prompt(mode)
        if kb_context:
            system_prompt = (
                system_prompt
                + f"\n\n## Retrieved Legal Context\n{kb_context}\n\nUse this context to inform your answer."
            )

        delimited_prompt = self._wrap_with_delimiters(sanitized)

        try:
            async for chunk in self._stream_ollama(system_prompt, delimited_prompt, **kwargs):
                yield chunk
            return
        except Exception as e:
            logger.warning("stream_ollama_failed", error=str(e))

        try:
            full_response = await self.route(prompt, mode, **kwargs)
            yield full_response
        except Exception:
            yield "I apologize, but I'm unable to process your streaming request at the moment."

    def _sanitize_user_input(self, text: str) -> str:
        injection_patterns = [
            (
                r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|above|earlier)\s+(?:instructions?|prompts?|rules?)",
                "",
            ),
            (r"you\s+are\s+now\s+(?:a|an)\s+\w+", ""),
            (r"system\s*:\s*", ""),
            (r"<\|im_start\|>", ""),
            (r"<\|im_end\|>", ""),
            (r"\[INST\]", ""),
            (r"\[/INST\]", ""),
        ]
        import re

        for pattern, replacement in injection_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _wrap_with_delimiters(self, user_text: str) -> str:
        return f"{DELIMITER_START}\n{user_text}\n{DELIMITER_END}"

    async def _route_ollama(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        client = await self._get_client()
        stream = kwargs.get("stream", False)

        ollama_messages = [
            {"role": "system", "content": system_prompt},
        ]

        try:
            loader = get_few_shot_loader()
            examples = loader.get_examples(max_examples=2)
            for ex in examples:
                ollama_messages.append({"role": "user", "content": ex.get("query", "")})
                ollama_messages.append({"role": "assistant", "content": ex.get("answer", "")})
        except Exception:
            pass

        ollama_messages.append({"role": "user", "content": user_prompt})

        start_time = time.time()
        if stream:
            return await self._stream_ollama_impl(client, ollama_messages)

        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": ollama_messages,
                "stream": False,
                "options": {"num_predict": 1000, "temperature": 0.3},
            },
        )
        latency = time.time() - start_time
        self._record_latency("ollama", latency)
        response.raise_for_status()
        return response.json()["message"]["content"]

    async def _stream_ollama(self, system_prompt: str, user_prompt: str, **kwargs) -> AsyncIterator[str]:
        client = await self._get_client()
        ollama_messages = [
            {"role": "system", "content": system_prompt},
        ]

        try:
            loader = get_few_shot_loader()
            examples = loader.get_examples(max_examples=2)
            for ex in examples:
                ollama_messages.append({"role": "user", "content": ex.get("query", "")})
                ollama_messages.append({"role": "assistant", "content": ex.get("answer", "")})
        except Exception:
            pass

        ollama_messages.append({"role": "user", "content": user_prompt})
        async for chunk in self._stream_ollama_impl(client, ollama_messages):
            yield chunk

    async def _stream_ollama_impl(self, client: httpx.AsyncClient, messages: list) -> AsyncIterator[str]:
        start_time = time.time()
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": True,
                "options": {"num_predict": 1000, "temperature": 0.3},
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        chunk = __import__("json").loads(line)
                        if "message" in chunk:
                            content = chunk["message"].get("content", "")
                            if content:
                                yield content
                        if chunk.get("done"):
                            break
                    except __import__("json").JSONDecodeError:
                        continue
        latency = time.time() - start_time
        self._record_latency("ollama", latency)

    def _get_kb_context(self, query: str) -> str:
        kb_path = "data/kb/offline_knowledge_base.json"
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                kb = __import__("json").load(f)
            q = query.lower().strip()
            matched = []
            for key in sorted(kb.keys(), key=lambda k: len(k), reverse=True):
                key_lower = key.lower().replace("_", " ")
                words = key_lower.split()
                if any(w in q for w in words) or key_lower in q:
                    entry = kb[key]
                    parts = [f"**{entry.get('title', key)}**"]
                    if entry.get("sections"):
                        parts.append(f"Sections: {entry['sections']}")
                    if entry.get("description"):
                        parts.append(entry["description"])
                    matched.append("\n".join(parts))
                    if len(matched) >= 3:
                        break
            return "\n\n---\n\n".join(matched) if matched else ""
        except Exception:
            return ""

    def _post_process_output(self, output: str, original_query: str) -> str:
        from app.ai.validators.query_validator import query_validator

        if not output or len(output) < 10:
            return output
        is_legal, _, _ = query_validator.is_legal_query(original_query)
        if not is_legal:
            return output
        import re

        output = re.sub(
            r"(?i)(IPC Section|Indian Penal Code|Section\s+\d+\s+IPC)",
            lambda m: m.group().replace("IPC", "BNS").replace("Indian Penal Code", "BNS (Bharatiya Nyaya Sanhita)"),
            output,
        )
        output = re.sub(
            r"(?i)(CrPC|Code of Criminal Procedure)",
            lambda m: m.group()
            .replace("CrPC", "BNSS")
            .replace("Code of Criminal Procedure", "BNSS (Bharatiya Nagarik Suraksha Sanhita)"),
            output,
        )
        output = re.sub(
            r"(?i)(Indian Evidence Act|Evidence Act)",
            lambda m: m.group()
            .replace("Indian Evidence Act", "BSA (Bharatiya Sakshya Adhiniyam)")
            .replace("Evidence Act", "BSA"),
            output,
        )
        return output

    async def _route_gemini(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key not configured")
        client = await self._get_client()
        url = f"{GEMINI_BASE_URL}/models/gemini-2.0-flash:generateContent?key={settings.gemini_api_key}"
        payload = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}]}
        start_time = time.time()
        response = await client.post(url, json=payload)
        latency = time.time() - start_time
        self._record_latency("gemini", latency)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _route_vector(self, query: str) -> Optional[str]:
        try:
            from app.ingestion.chroma.vector_store import query_vector_store

            context = await query_vector_store(query, n_results=5)
            if context and len(context) > 50:
                return context
            return None
        except Exception as e:
            logger.error("vector_search_failed", error=str(e))
            return None

    async def _route_graph(self, query: str) -> Optional[str]:
        try:
            from app.graph.neo4j import Neo4jManager

            manager = Neo4jManager()
            start_time = time.time()
            result = await manager.search_similar(query, top_k=5)
            latency = time.time() - start_time
            if result:
                context = "\n".join([f"- {r.get('name', '')}: {r.get('description', '')}" for r in result])
                return f"Legal knowledge graph results:\n{context}\n\nQuery: {query}"
            return None
        except Exception as e:
            logger.warning("graph_query_failed", error=str(e))
            return None

    def _route_offline(self, query: str) -> str:
        kb_path = "data/kb/offline_knowledge_base.json"
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                kb = __import__("json").load(f)
            q = query.lower().strip()
            sorted_keys = sorted(kb.keys(), key=lambda k: len(k), reverse=True)
            for key in sorted_keys:
                key_lower = key.lower().replace("_", " ")
                words = key_lower.split()
                if any(w in q for w in words) or key_lower in q:
                    entry = kb[key]
                    parts = [f"**{entry.get('title', key)}**"]
                    if entry.get("sections"):
                        parts.append(f"*Relevant Sections:* {entry['sections']}")
                    if entry.get("description"):
                        parts.append(f"\n{entry['description']}")
                    if entry.get("procedure"):
                        parts.append(f"\n**Procedure:**\n{entry['procedure']}")
                    if entry.get("punishment"):
                        parts.append(f"\n**Punishment:**\n{entry['punishment']}")
                    if entry.get("bail"):
                        parts.append(f"\n**Bail:**\n{entry['bail']}")
                    if entry.get("factors"):
                        parts.append(f"\n**Factors:**\n{entry['factors']}")
                    if entry.get("rights"):
                        parts.append(f"\n**Rights:**\n{entry['rights']}")
                    if entry.get("requirements"):
                        parts.append(f"\n**Requirements:**\n{entry['requirements']}")
                    if entry.get("limitation"):
                        parts.append(f"\n**Limitation:**\n{entry['limitation']}")
                    if entry.get("reporting"):
                        parts.append(f"\n**Reporting:**\n{entry['reporting']}")
                    if entry.get("citation"):
                        parts.append(f"\n*Citation:* {entry['citation']}")
                    parts.append(
                        "\n\n*This is general legal information and not legal advice. For specific legal assistance, please consult a qualified lawyer.*"
                    )
                    return "\n\n".join(parts)
            return self._get_fallback_response(query)
        except Exception:
            return self._get_fallback_response(query)

    def _get_fallback_response(self, query: str) -> str:
        return (
            f"I can provide general legal information based on the Bharatiya Nyaya Sanhita (BNS), "
            f"Bharatiya Nagarik Suraksha Sanhita (BNSS), and Bharatiya Sakshya Adhiniyam (BSA). "
            f"Regarding your query about '{query[:100]}...', please note that this is general legal "
            f"information and not legal advice. For specific legal assistance, please consult a qualified lawyer."
        )

    def _record_latency(self, provider: str, latency: float):
        self._latency[provider].append(latency)
        if len(self._latency[provider]) > 100:
            self._latency[provider] = self._latency[provider][-100:]

    def get_stats(self) -> dict:
        stats = {"health": self._health, "latency": {}, "circuit_breakers": {}}
        for provider in ["ollama", "gemini"]:
            latencies = self._latency[provider]
            if latencies:
                stats["latency"][provider] = {
                    "avg": sum(latencies) / len(latencies),
                    "min": min(latencies),
                    "max": max(latencies),
                    "samples": len(latencies),
                }
            stats["circuit_breakers"][provider] = self._circuit_breakers[provider].state
        return stats


llm_router = LLMRouter()


def direct_kb_response(query: str) -> str | None:
    import json
    import os

    _this_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        "data/kb/offline_knowledge_base.json",
        os.path.join(_this_dir, "..", "..", "..", "..", "data", "kb", "offline_knowledge_base.json"),
        os.path.join(os.getcwd(), "data", "kb", "offline_knowledge_base.json"),
    ]
    kb = None
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    kb = json.load(f)
                break
            except Exception:
                continue
    if kb is None:
        return None
    q = query.lower().strip()
    sorted_keys = sorted(kb.keys(), key=lambda k: len(k), reverse=True)
    for key in sorted_keys:
        key_lower = key.lower().replace("_", " ")
        words = key_lower.split()
        if any(w in q for w in words) or key_lower in q:
            entry = kb[key]
            parts = [f"**{entry.get('title', key)}**"]
            if entry.get("sections"):
                parts.append(f"*Relevant Sections:* {entry['sections']}")
            if entry.get("description"):
                parts.append(f"\n{entry['description']}")
            if entry.get("procedure"):
                parts.append(f"\n**Procedure:**\n{entry['procedure']}")
            if entry.get("punishment"):
                parts.append(f"\n**Punishment:**\n{entry['punishment']}")
            if entry.get("bail"):
                parts.append(f"\n**Bail:**\n{entry['bail']}")
            if entry.get("factors"):
                parts.append(f"\n**Factors:**\n{entry['factors']}")
            if entry.get("rights"):
                parts.append(f"\n**Rights:**\n{entry['rights']}")
            if entry.get("requirements"):
                parts.append(f"\n**Requirements:**\n{entry['requirements']}")
            if entry.get("limitation"):
                parts.append(f"\n**Limitation:**\n{entry['limitation']}")
            if entry.get("reporting"):
                parts.append(f"\n**Reporting:**\n{entry['reporting']}")
            if entry.get("citation"):
                parts.append(f"\n*Citation:* {entry['citation']}")
            parts.append(
                "\n\n*This is general legal information and not legal advice. For specific legal assistance, please consult a qualified lawyer.*"
            )
            return "\n\n".join(parts)
    return None


def generate_fallback_response(query: str) -> str:
    return (
        f"I can provide general legal information based on the Bharatiya Nyaya Sanhita (BNS), "
        f"Bharatiya Nagarik Suraksha Sanhita (BNSS), and Bharatiya Sakshya Adhiniyam (BSA). "
        f"Regarding your query about '{query[:100]}...', please note that this is general legal "
        f"information and not legal advice. For specific legal assistance, please consult a qualified lawyer."
    )


async def process_with_llm(prompt: str, context: dict = None) -> str:
    return await llm_router.route(prompt, "general")
