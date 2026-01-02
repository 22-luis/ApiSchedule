from typing import Dict, Any
from app.shared.core.config import settings
from app.shared.utils.core.health_checks import get_health_status, get_quick_health_status

class MonitoringService:
    @staticmethod
    async def get_app_info() -> Dict[str, Any]:
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "database_configured": bool(settings.SQLALCHEMY_DATABASE_URI),
            "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED,
            "cors_origins": settings.CORS_ORIGINS,
            "working_hours": {
                "monday_friday": settings.WORKING_HOURS_MONDAY_FRIDAY,
                "saturday": settings.WORKING_HOURS_SATURDAY,
                "sunday": settings.WORKING_HOURS_SUNDAY
            }
        }

    @staticmethod
    async def get_health(detailed: bool = False) -> Dict[str, Any]:
        if detailed:
            return await get_health_status()
        return await get_quick_health_status()

monitoring_service = MonitoringService()