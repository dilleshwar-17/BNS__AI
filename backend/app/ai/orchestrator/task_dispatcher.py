from app.logging import get_logger

logger = get_logger(__name__)


class TaskDispatcher:
    def __init__(self):
        self.agents = {}

    def register(self, task_type: str, agent):
        self.agents[task_type] = agent
        logger.info("agent_registered", task_type=task_type, agent=agent.__class__.__name__)

    async def dispatch(self, task_type: str, payload: dict):
        agent = self.agents.get(task_type)
        if not agent:
            logger.warning("no_agent_for_task", task_type=task_type)
            return None
        return await agent.process(payload)
