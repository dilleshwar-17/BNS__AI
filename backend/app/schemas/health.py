from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: str
    statistics: dict | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    services: dict[str, ServiceStatus]
