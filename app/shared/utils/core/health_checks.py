import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.shared.core.config import settings
from app.shared.db.session import engine
from app.shared.utils.core.logging import get_logger

logger = get_logger("health_checks")


class HealthChecker:
    
    def __init__(self):
        self.start_time = time.time()
        self.last_db_check = None
        self.db_check_interval = 30  # segundos
    
    async def check_database_connection(self) -> Dict[str, Any]:
        try:
            # Verificar si ya hicimos una verificación reciente
            if (self.last_db_check and 
                time.time() - self.last_db_check < self.db_check_interval):
                return {
                    "status": "healthy",
                    "message": "Database connection cached",
                    "cached": True
                }
            
            # Realizar verificación de conexión
            with engine.connect() as connection:
                # Verificar conexión básica
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
                
                # Verificar versión de PostgreSQL
                version_result = connection.execute(text("SELECT version()"))
                version = version_result.fetchone()[0]
                
                # Verificar tiempo de respuesta
                start_time = time.time()
                connection.execute(text("SELECT 1"))
                response_time = (time.time() - start_time) * 1000  # en ms
                
                self.last_db_check = time.time()
                
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "version": version,
                    "response_time_ms": round(response_time, 2),
                    "cached": False
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
                "error": str(e),
                "cached": False
            }
    
    async def check_memory_usage(self) -> Dict[str, Any]:
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            return {
                "status": "healthy" if memory.percent < 90 else "warning",
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent,
                "message": "Memory usage normal" if memory.percent < 90 else "High memory usage"
            }
        except ImportError:
            return {
                "status": "unknown",
                "message": "psutil not available for memory monitoring"
            }
        except Exception as e:
            logger.error(f"Memory health check failed: {e}")
            return {
                "status": "error",
                "message": f"Memory check failed: {str(e)}"
            }
    
    async def check_disk_usage(self) -> Dict[str, Any]:
        try:
            import psutil
            
            disk = psutil.disk_usage('/')
            return {
                "status": "healthy" if disk.percent < 90 else "warning",
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_percent": disk.percent,
                "message": "Disk usage normal" if disk.percent < 90 else "High disk usage"
            }
        except ImportError:
            return {
                "status": "unknown",
                "message": "psutil not available for disk monitoring"
            }
        except Exception as e:
            logger.error(f"Disk health check failed: {e}")
            return {
                "status": "error",
                "message": f"Disk check failed: {str(e)}"
            }
    
    async def check_rate_limiting(self) -> Dict[str, Any]:
        try:
            from app.shared.utils.performance.rate_limiting import get_rate_limit_stats
            
            stats = get_rate_limit_stats()
            return {
                "status": "healthy",
                "enabled": settings.RATE_LIMIT_ENABLED,
                "stats": stats,
                "message": "Rate limiting system operational"
            }
        except Exception as e:
            logger.error(f"Rate limiting health check failed: {e}")
            return {
                "status": "error",
                "message": f"Rate limiting check failed: {str(e)}"
            }
    
    async def check_configuration(self) -> Dict[str, Any]:
        try:
            # Verificar variables críticas
            critical_vars = {
                "SECRET_KEY": settings.SECRET_KEY,
                "POSTGRES_USER": settings.POSTGRES_USER,
                "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
                "POSTGRES_DB": settings.POSTGRES_DB,
                "POSTGRES_SERVER": settings.POSTGRES_SERVER,
                "POSTGRES_PORT": settings.POSTGRES_PORT
            }
            
            missing_vars = [var for var, value in critical_vars.items() if not value]
            
            if missing_vars:
                return {
                    "status": "unhealthy",
                    "message": f"Missing critical configuration variables: {', '.join(missing_vars)}",
                    "missing_vars": missing_vars
                }
            
            return {
                "status": "healthy",
                "message": "All critical configuration variables are set",
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG
            }
            
        except Exception as e:
            logger.error(f"Configuration health check failed: {e}")
            return {
                "status": "error",
                "message": f"Configuration check failed: {str(e)}"
            }
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        start_time = time.time()
        
        # Ejecutar todas las verificaciones en paralelo
        tasks = [
            self.check_database_connection(),
            self.check_memory_usage(),
            self.check_disk_usage(),
            self.check_rate_limiting(),
            self.check_configuration()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        checks = {
            "database": results[0] if not isinstance(results[0], Exception) else {
                "status": "error",
                "message": f"Database check failed: {str(results[0])}"
            },
            "memory": results[1] if not isinstance(results[1], Exception) else {
                "status": "error",
                "message": f"Memory check failed: {str(results[1])}"
            },
            "disk": results[2] if not isinstance(results[2], Exception) else {
                "status": "error",
                "message": f"Disk check failed: {str(results[2])}"
            },
            "rate_limiting": results[3] if not isinstance(results[3], Exception) else {
                "status": "error",
                "message": f"Rate limiting check failed: {str(results[3])}"
            },
            "configuration": results[4] if not isinstance(results[4], Exception) else {
                "status": "error",
                "message": f"Configuration check failed: {str(results[4])}"
            }
        }
        
        # Determinar estado general
        overall_status = "healthy"
        if any(check["status"] == "unhealthy" for check in checks.values()):
            overall_status = "unhealthy"
        elif any(check["status"] == "warning" for check in checks.values()):
            overall_status = "warning"
        elif any(check["status"] == "error" for check in checks.values()):
            overall_status = "error"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": round(time.time() - self.start_time, 2),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "checks": checks,
            "app_info": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT
            }
        }


# Instancia global del health checker
health_checker = HealthChecker()


async def get_health_status() -> Dict[str, Any]:
    return await health_checker.comprehensive_health_check()


async def get_quick_health_status() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": round(time.time() - health_checker.start_time, 2),
        "app_info": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT
        }
    }
