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
    name: str = Field(..., alias="app_name")
    version: str
    environment: str

class HealthStatusOut(BaseModel):
    status: str
    timestamp: str
    uptime: float
    app_info: HealthAppInfo

class DetailsHealthStatusOut(BaseModel):
    status: str
    message: str
    cached: Optional[bool] = None
    version: Optional[str] = None
    response_time: Optional[float] = None
    used_percentage: Optional[float] = None
    total_gb: Optional[float] = None
    available_gb: Optional[float] = None
    free_gb: Optional[float] = None
    enabled: Optional[bool] = None
    stats: Optional[Dict[str, Any]] = None
    missing_vars: Optional[List[str]] = None
    environment: Optional[str] = None
    debugging: Optional[bool] = None

class SystemStatusOut(BaseModel):
    status: str = "ok"
    date: Dict[str, Any]

