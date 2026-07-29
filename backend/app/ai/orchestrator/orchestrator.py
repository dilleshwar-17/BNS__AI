import time
import uuid
from typing import Any

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.intent_agent import classifier_agent
from app.ai.agents.knowledge_agent import kg_agent
from app.ai.agents.learning_agent import learning_agent
from app.ai.agents.retrieval_agent import retrieval_agent
from app.ai.orchestrator.workflow_router import Message, web
from app.ai.prompts.prompt_builder import prompt_builder
from app.ai.validators.query_validator import verifier_agent
from app.ai.validators.response_validator import response_verifier
from app.core.logging import get_logger

logger = get_logger(__name__)


class MasterAgent(BaseAgent):
    def __init__(self):
        super().__init__("master", "Central orchestrator weaving all agents into a spider web")
        self.subscribe_to("full_cycle")
        self.subscribe_to("master_status")
        self.running = False
        self.cycle_count = 0
        self.cycle_history = []

    def start(self):
        super().start()
        classifier_agent.start()
        verifier_agent.start()
        retrieval_agent.start()
        kg_agent.start()
        prompt_builder.start()
        response_verifier.start()
        learning_agent.start()
        self.running = True
        logger.info(
            "spider_web_fully_operational",
            agents=[
                "master",
                "classifier",
                "verifier",
                "retrieval",
                "kg",
                "prompt_builder",
                "response_verifier",
                "learning",
            ],
        )

    def stop(self):
        self.running = False
        for agent in [
            classifier_agent,
            verifier_agent,
            retrieval_agent,
            kg_agent,
            prompt_builder,
            response_verifier,
            learning_agent,
        ]:
            agent.stop()
        super().stop()
        logger.info("spider_web_shutdown")

    async def process(self, message: Message) -> Any:
        if message.type == "full_cycle":
            return await self.run_full_cycle(message.payload)
        elif message.type == "master_status":
            return self.get_status()
        return {"error": "Unknown master command"}

    async def run_full_cycle(self, payload: dict) -> dict:
        cycle_id = str(uuid.uuid4())
        start_time = time.time()
        self.cycle_count += 1

        query = payload.get("query", "")
        user_id = payload.get("user_id")
        mode = payload.get("mode", "legal_guidance")
        rating = payload.get("rating", 0)
        top_k = payload.get("top_k", 10)

        logger.info("full_cycle_started", cycle=cycle_id, query=query[:60], user=user_id)

        # Step 1: Classify
        self.log("step", cycle=cycle_id, step="classification")
        classification_result = await self.publish(
            "classify_query",
            {
                "query": query,
                "user_id": user_id,
            },
        )

        # Extract the classifier's response
        classification = self._extract_agent_result(
            classification_result,
            {
                "primary_type": mode,
                "confidence": 0.5,
                "complexity": "medium",
                "sections": [],
                "topics": [],
                "entities": [],
            },
        )

        # Step 2: Verify query
        self.log("step", cycle=cycle_id, step="query_verification")
        verification_result = await self.publish(
            "verify_query",
            {
                "query": query,
                "classification": classification,
            },
        )
        query_verification = self._extract_agent_result(
            verification_result,
            {
                "verified": True,
                "score": 1.0,
                "issues": [],
                "suggestions": [],
            },
        )

        # Step 3: Retrieve from all sources
        self.log("step", cycle=cycle_id, step="retrieval")
        retrieval_result = await self.publish(
            "retrieve",
            {
                "query": query,
                "classification": classification,
                "user_id": user_id,
            },
        )
        retrieval_data = self._extract_agent_result(
            retrieval_result,
            {
                "context": "",
                "results": [],
                "strategies_used": [],
                "total_fused": 0,
                "breakdown": {},
            },
        )

        # Step 4: Graph enrichment
        self.log("step", cycle=cycle_id, step="graph_enrichment")
        graph_queries = classification.get("sections", [])
        if classification.get("primary_type"):
            graph_queries.append(classification["primary_type"])

        graph_result = await self.publish(
            "graph_query",
            {
                "query": query,
                "type": classification.get("primary_type", ""),
                "sections": classification.get("sections", []),
            },
        )
        graph_data = self._extract_agent_result(graph_result, {"results": []})

        # Step 5: Build prompt
        self.log("step", cycle=cycle_id, step="prompt_building")
        prompt_result = await self.publish(
            "build_prompt",
            {
                "query": query,
                "context": retrieval_data.get("context", ""),
                "classification": classification,
                "user_id": user_id,
            },
        )
        prompt_data = self._extract_agent_result(
            prompt_result,
            {
                "prompt": "",
                "template_used": "default",
            },
        )

        # Step 6: Generate response (via LLM router)
        self.log("step", cycle=cycle_id, step="response_generation")
        from app.ai.llms.router import llm_router

        generated_prompt = prompt_data.get("prompt", query)
        response_text = await llm_router.route(generated_prompt, classification.get("primary_type", mode))

        # Step 7: Verify response
        self.log("step", cycle=cycle_id, step="response_verification")
        response_verification_result = await self.publish(
            "verify_response",
            {
                "query": query,
                "response": response_text,
                "context": retrieval_data.get("context", ""),
                "classification": classification,
            },
        )
        response_quality = self._extract_agent_result(
            response_verification_result,
            {
                "verified": True,
                "quality_score": 0.7,
            },
        )

        # Step 8: Learn from cycle
        self.log("step", cycle=cycle_id, step="learning")
        await self.publish(
            "full_cycle_result",
            {
                "query": query,
                "classification": classification,
                "retrieval": retrieval_data,
                "prompt": prompt_data.get("prompt", ""),
                "response": response_text,
                "verification": response_quality,
                "user_id": user_id,
                "rating": rating,
            },
        )

        elapsed = time.time() - start_time

        # Step 9: Send graph learning if there were results
        if retrieval_data.get("results"):
            for r in retrieval_data["results"][:3]:
                source = r.get("source", "unknown")
                if source != "unknown":
                    await self.publish(
                        "graph_learn",
                        {
                            "source": f"query:{query[:30]}",
                            "target": f"source:{source}",
                            "relation": "RETRIEVED_FROM",
                        },
                    )

        result = {
            "cycle_id": cycle_id,
            "query": query,
            "response": response_text,
            "classification": classification,
            "query_verification": query_verification,
            "retrieval": {
                "strategies": retrieval_data.get("strategies_used", []),
                "total_results": retrieval_data.get("total_fused", 0),
                "breakdown": retrieval_data.get("breakdown", {}),
                "context_preview": retrieval_data.get("context", "")[:300],
            },
            "graph_enrichment": {
                "total": graph_data.get("total", len(graph_data.get("results", []))),
            },
            "prompt": {
                "template": prompt_data.get("template_used", "default"),
                "tokens": prompt_data.get("estimated_tokens", 0),
            },
            "response_quality": response_quality,
            "elapsed_seconds": round(elapsed, 3),
            "spider_web_status": "operational",
        }

        self.cycle_history.append(
            {
                "cycle_id": cycle_id,
                "query": query[:50],
                "elapsed": elapsed,
                "quality": response_quality.get("quality_score", 0),
                "type": classification.get("primary_type", "unknown"),
            }
        )
        if len(self.cycle_history) > 100:
            self.cycle_history = self.cycle_history[-100:]

        logger.info(
            "full_cycle_completed",
            cycle=cycle_id,
            elapsed=round(elapsed, 3),
            quality=response_quality.get("quality_score"),
        )

        return result

    def _extract_agent_result(self, publish_results: list, default: Any) -> Any:
        if not publish_results:
            return default
        for r in publish_results:
            if isinstance(r, dict) and "result" in r and r["result"] is not None:
                if isinstance(r["result"], dict):
                    return r["result"]
        return default

    def get_status(self) -> dict:
        web_stats = web.get_stats()
        cycles = self.cycle_history[-10:] if self.cycle_history else []
        avg_elapsed = (
            sum(c["elapsed"] for c in self.cycle_history) / len(self.cycle_history) if self.cycle_history else 0
        )
        avg_quality = (
            sum(c["quality"] for c in self.cycle_history) / len(self.cycle_history) if self.cycle_history else 0
        )

        return {
            "agent": "master",
            "status": "operational" if self.running else "stopped",
            "cycles_completed": self.cycle_count,
            "average_elapsed": round(avg_elapsed, 3),
            "average_quality": round(avg_quality, 3),
            "recent_cycles": cycles,
            "spider_web": web_stats,
            "agents_active": [
                "classifier",
                "verifier",
                "retrieval",
                "kg",
                "prompt_builder",
                "response_verifier",
                "learning",
            ],
        }


master_agent = MasterAgent()
