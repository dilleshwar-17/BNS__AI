import asyncio
from abc import ABC
from collections import OrderedDict
from typing import Any, Dict

from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_USER_PROFILES = 1000
USER_PROFILE_EVICT_BATCH = 100


class BaseAgent(ABC):
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.user_profiles: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._active_tasks: Dict[str, asyncio.Task] = {}

    def _evict_profiles_if_needed(self):
        if len(self.user_profiles) > MAX_USER_PROFILES:
            evicted = 0
            while len(self.user_profiles) > MAX_USER_PROFILES - USER_PROFILE_EVICT_BATCH and self.user_profiles:
                self.user_profiles.popitem(last=False)
                evicted += 1
            if evicted > 0:
                logger.info("profile_evicted", agent=self.name, count=evicted, remaining=len(self.user_profiles))

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        if user_id in self.user_profiles:
            self.user_profiles.move_to_end(user_id)
            return self.user_profiles[user_id]
        return {}

    def update_user_profile(self, user_id: str, updates: Dict[str, Any]):
        self._evict_profiles_if_needed()
        if user_id in self.user_profiles:
            self.user_profiles[user_id].update(updates)
            self.user_profiles.move_to_end(user_id)
        else:
            self.user_profiles[user_id] = updates

    def subscribe_to(self, topic: str):
        pass

    def start(self):
        logger.info("agent_started", agent=self.name)

    def stop(self):
        for task in self._active_tasks.values():
            if not task.done():
                task.cancel()
        self._active_tasks.clear()
        logger.info("agent_stopped", agent=self.name)

    def _log_agent_error(self, context: str, error: Exception, user_id: str = None):
        logger.error(
            "agent_error",
            agent=self.name,
            context=context,
            error=str(error),
            error_type=type(error).__name__,
            user_id=user_id,
        )

    async def run_full_cycle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user_id = payload.get("user_id")
        try:
            return await self._process(payload)
        except Exception as e:
            self._log_agent_error("run_full_cycle", e, user_id)
            return {"error": str(e), "agent": self.name}

    async def _process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"error": "not implemented"}
