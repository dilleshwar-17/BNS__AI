import time
import uuid

from app.logging import get_logger

logger = get_logger(__name__)


class ExecutionManager:
    def __init__(self):
        self.active_executions: dict = {}

    async def execute(self, workflow_fn, payload: dict) -> dict:
        execution_id = str(uuid.uuid4())
        start = time.time()
        self.active_executions[execution_id] = {"status": "running", "start": start}
        try:
            result = await workflow_fn(payload)
            elapsed = time.time() - start
            self.active_executions[execution_id] = {"status": "completed", "elapsed": elapsed}
            logger.info("execution_completed", execution_id=execution_id, elapsed=round(elapsed, 3))
            return result
        except Exception as e:
            elapsed = time.time() - start
            self.active_executions[execution_id] = {"status": "failed", "error": str(e)}
            logger.error("execution_failed", execution_id=execution_id, error=str(e))
            raise
