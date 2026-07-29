from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLM(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass
