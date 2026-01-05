from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class WorkingHours(BaseModel):
    monday_friday: str
    saturday: str
    sunday: str

class AppInfoOut(BaseModel):
    app_name: str
    version: str
    environment: str
    debug: bool
    database_configured: str
    rate_limiting_enabled: bool
    cors_origins: List[str]
    working_hours: WorkingHours

class HealthAppInfo(BaseModel):
    name: str
    version: str
    environment: str

class HealthStatusOut(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    app_info: HealthAppInfo

class DetailsHealthStatusOut(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    response_time_ms: float
    checks: Dict[str, Any]
    app_info: HealthAppInfo

class SystemStatusOut(BaseModel):
    status: str = "ok"
    date: Dict[str, Any]

