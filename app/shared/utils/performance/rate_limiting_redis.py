"""
Sistema de rate limiting con Redis para entornos de producción.
Proporciona rate limiting distribuido y persistente.
"""
import time
import hashlib
import json
from typing import Dict, Optional, Tuple, Any
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from app.shared.core.config import settings
from app.shared.utils.core.logging import get_logger, log_security_event

logger = get_logger("rate_limiting_redis")


class RedisRateLimiter:
    """
    Implementación de rate limiting usando Redis.
    
    Esta clase proporciona rate limiting distribuido que funciona
    en entornos con múltiples instancias de la aplicación.
    """
    
    def __init__(self, redis_client=None):
        """
        Inicializa el rate limiter con Redis.
        
        Args:
            redis_client: Cliente Redis opcional. Si no se proporciona,
                         se intentará crear uno usando la configuración.
        """
        self.redis_client = redis_client
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Inicializa la conexión a Redis"""
        if self.redis_client is None:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=settings.REDIS_HOST if hasattr(settings, 'REDIS_HOST') else 'localhost',
                    port=settings.REDIS_PORT if hasattr(settings, 'REDIS_PORT') else 6379,
                    db=settings.REDIS_DB if hasattr(settings, 'REDIS_DB') else 0,
                    password=settings.REDIS_PASSWORD if hasattr(settings, 'REDIS_PASSWORD') else None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Verificar conexión
                self.redis_client.ping()
                logger.info("Redis rate limiting initialized successfully")
            except ImportError:
                logger.warning("Redis not available, falling back to in-memory rate limiting")
                self.redis_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                self.redis_client = None
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Obtiene la IP real del cliente.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            str: IP del cliente
        """
        # Verificar headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _get_user_identifier(self, request: Request) -> Optional[str]:
        """
        Obtiene el identificador del usuario si está autenticado.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Optional[str]: Hash del token de usuario o None
        """
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return hashlib.md5(token.encode()).hexdigest()
        return None
    
    def _get_redis_key(self, identifier: str, prefix: str) -> str:
        """
        Genera una clave Redis para el rate limiting.
        
        Args:
            identifier: Identificador (IP o user_id)
            prefix: Prefijo para el tipo de límite
            
        Returns:
            str: Clave Redis formateada
        """
        return f"rate_limit:{prefix}:{identifier}"
    
    def _get_blocked_key(self, identifier: str, prefix: str) -> str:
        """
        Genera una clave Redis para el bloqueo.
        
        Args:
            identifier: Identificador (IP o user_id)
            prefix: Prefijo para el tipo de bloqueo
            
        Returns:
            str: Clave Redis formateada
        """
        return f"rate_limit:blocked:{prefix}:{identifier}"
    
    def check_rate_limit(
        self, 
        request: Request, 
        max_requests: int = None,
        window_seconds: int = 60,
        block_duration: int = 300
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica si la request está dentro de los límites de velocidad usando Redis.
        
        Args:
            request: FastAPI Request object
            max_requests: Máximo número de requests permitidas
            window_seconds: Ventana de tiempo en segundos
            block_duration: Duración del bloqueo en segundos
            
        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, {"enabled": False}
        
        if not self.redis_client:
            # Fallback a rate limiting en memoria
            from app.shared.utils.performance.rate_limiting import RateLimiter
            fallback_limiter = RateLimiter()
            return fallback_limiter.check_rate_limit(request, max_requests, window_seconds, block_duration)
        
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_identifier(request)
        
        if max_requests is None:
            max_requests = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        
        try:
            current_time = time.time()
            
            # Verificar bloqueos
            if self._is_blocked(client_ip, "ip", block_duration):
                log_security_event("rate_limit_ip_blocked", details={"ip": client_ip})
                return False, {
                    "blocked": True,
                    "type": "ip",
                    "identifier": client_ip,
                    "retry_after": block_duration
                }
            
            if user_id and self._is_blocked(user_id, "user", block_duration):
                log_security_event("rate_limit_user_blocked", user_id=user_id)
                return False, {
                    "blocked": True,
                    "type": "user",
                    "identifier": user_id,
                    "retry_after": block_duration
                }
            
            # Verificar límites por IP
            ip_key = self._get_redis_key(client_ip, "ip")
            ip_requests = self._get_requests_count(ip_key, current_time, window_seconds)
            
            if ip_requests >= max_requests:
                self._block_identifier(client_ip, "ip", block_duration)
                log_security_event("rate_limit_ip_exceeded", details={
                    "ip": client_ip,
                    "requests": ip_requests,
                    "limit": max_requests
                })
                return False, {
                    "exceeded": True,
                    "type": "ip",
                    "identifier": client_ip,
                    "requests": ip_requests,
                    "limit": max_requests,
                    "retry_after": block_duration
                }
            
            # Verificar límites por usuario
            if user_id:
                user_key = self._get_redis_key(user_id, "user")
                user_max_requests = max_requests // 2
                user_requests = self._get_requests_count(user_key, current_time, window_seconds)
                
                if user_requests >= user_max_requests:
                    self._block_identifier(user_id, "user", block_duration)
                    log_security_event("rate_limit_user_exceeded", user_id=user_id, details={
                        "requests": user_requests,
                        "limit": user_max_requests
                    })
                    return False, {
                        "exceeded": True,
                        "type": "user",
                        "identifier": user_id,
                        "requests": user_requests,
                        "limit": user_max_requests,
                        "retry_after": block_duration
                    }
            
            # Registrar la request actual
            self._add_request(ip_key, current_time)
            if user_id:
                self._add_request(user_key, current_time)
            
            # Calcular información de rate limit
            remaining_ip = max(0, max_requests - ip_requests - 1)
            remaining_user = max(0, user_max_requests - user_requests - 1) if user_id else None
            
            return True, {
                "enabled": True,
                "ip_requests": ip_requests + 1,
                "ip_limit": max_requests,
                "ip_remaining": remaining_ip,
                "user_requests": user_requests + 1 if user_id else None,
                "user_limit": user_max_requests if user_id else None,
                "user_remaining": remaining_user
            }
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fallback a rate limiting en memoria en caso de error
            from app.shared.utils.performance.rate_limiting import RateLimiter
            fallback_limiter = RateLimiter()
            return fallback_limiter.check_rate_limit(request, max_requests, window_seconds, block_duration)
    
    def _is_blocked(self, identifier: str, prefix: str, block_duration: int) -> bool:
        """
        Verifica si un identificador está bloqueado.
        
        Args:
            identifier: Identificador a verificar
            prefix: Prefijo del tipo de bloqueo
            block_duration: Duración del bloqueo
            
        Returns:
            bool: True si está bloqueado
        """
        blocked_key = self._get_blocked_key(identifier, prefix)
        blocked_time = self.redis_client.get(blocked_key)
        
        if blocked_time:
            blocked_time = float(blocked_time)
            if time.time() - blocked_time < block_duration:
                return True
            else:
                # Remover bloqueo expirado
                self.redis_client.delete(blocked_key)
        
        return False
    
    def _block_identifier(self, identifier: str, prefix: str, block_duration: int):
        """
        Bloquea un identificador por la duración especificada.
        
        Args:
            identifier: Identificador a bloquear
            prefix: Prefijo del tipo de bloqueo
            block_duration: Duración del bloqueo
        """
        blocked_key = self._get_blocked_key(identifier, prefix)
        self.redis_client.setex(blocked_key, block_duration, time.time())
    
    def _get_requests_count(self, key: str, current_time: float, window_seconds: int) -> int:
        """
        Obtiene el número de requests en la ventana de tiempo.
        
        Args:
            key: Clave Redis
            current_time: Tiempo actual
            window_seconds: Ventana de tiempo
            
        Returns:
            int: Número de requests
        """
        cutoff_time = current_time - window_seconds
        
        # Obtener todas las requests
        requests = self.redis_client.zrangebyscore(key, cutoff_time, '+inf')
        
        # Limpiar requests antiguas
        self.redis_client.zremrangebyscore(key, '-inf', cutoff_time)
        
        return len(requests)
    
    def _add_request(self, key: str, timestamp: float):
        """
        Agrega una nueva request al historial.
        
        Args:
            key: Clave Redis
            timestamp: Timestamp de la request
        """
        self.redis_client.zadd(key, {str(timestamp): timestamp})
        # Establecer TTL para limpiar automáticamente
        self.redis_client.expire(key, 3600)  # 1 hora
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del rate limiting.
        
        Returns:
            Dict con estadísticas del sistema
        """
        if not self.redis_client:
            return {"error": "Redis not available"}
        
        try:
            # Obtener todas las claves de rate limiting
            ip_keys = self.redis_client.keys("rate_limit:ip:*")
            user_keys = self.redis_client.keys("rate_limit:user:*")
            blocked_keys = self.redis_client.keys("rate_limit:blocked:*")
            
            stats = {
                "total_ip_entries": len(ip_keys),
                "total_user_entries": len(user_keys),
                "total_blocked": len(blocked_keys),
                "redis_connected": True
            }
            
            # Contar requests activas por IP
            active_ip_requests = 0
            for key in ip_keys:
                count = self.redis_client.zcard(key)
                active_ip_requests += count
            
            stats["active_ip_requests"] = active_ip_requests
            
            # Contar requests activas por usuario
            active_user_requests = 0
            for key in user_keys:
                count = self.redis_client.zcard(key)
                active_user_requests += count
            
            stats["active_user_requests"] = active_user_requests
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {"error": f"Failed to get stats: {str(e)}"}


# Instancia global del rate limiter con Redis
redis_rate_limiter = RedisRateLimiter()


async def redis_rate_limit_middleware(request: Request, call_next):
    """
    Middleware de rate limiting usando Redis.
    
    Args:
        request: FastAPI Request object
        call_next: Función para continuar con el siguiente middleware
        
    Returns:
        Response: Respuesta de la aplicación
    """
    is_allowed, rate_limit_info = redis_rate_limiter.check_rate_limit(request)
    
    if not is_allowed:
        # Crear respuesta de error con headers apropiados
        response_data = {
            "error": "Rate limit exceeded",
            "message": "Too many requests",
            "retry_after": rate_limit_info.get("retry_after", 300)
        }
        
        response = JSONResponse(
            status_code=429,
            content=response_data
        )
        
        # Agregar headers de rate limiting
        response.headers["Retry-After"] = str(rate_limit_info.get("retry_after", 300))
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + rate_limit_info.get("retry_after", 300)))
        
        return response
    
    # Continuar con la request
    response = await call_next(request)
    
    # Agregar headers de rate limiting a la respuesta exitosa
    if "ip_remaining" in rate_limit_info:
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("ip_limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.get("ip_remaining", 0))
    
    return response


def get_redis_rate_limit_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas del rate limiting con Redis.
    
    Returns:
        Dict con estadísticas del sistema
    """
    return redis_rate_limiter.get_stats()
