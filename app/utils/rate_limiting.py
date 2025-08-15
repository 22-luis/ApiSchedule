"""
Sistema de rate limiting para proteger la API de abuso.
Implementa límites de velocidad por IP y por usuario.
"""
import time
import hashlib
from typing import Dict, Optional, Tuple
from collections import defaultdict
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.utils.logging import get_logger, log_security_event


logger = get_logger("rate_limiting")


class RateLimiter:
    """Implementación simple de rate limiting en memoria"""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}
        self.blocked_users: Dict[str, float] = {}
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtiene la IP real del cliente"""
        # Verificar headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _get_user_identifier(self, request: Request) -> Optional[str]:
        """Obtiene el identificador del usuario si está autenticado"""
        # Intentar obtener el token de autorización
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Crear un hash del token para usarlo como identificador
            return hashlib.md5(token.encode()).hexdigest()
        return None
    
    def _clean_old_requests(self, key: str, window_seconds: int = 60) -> None:
        """Limpia requests antiguos del historial"""
        current_time = time.time()
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time < window_seconds
        ]
    
    def _is_blocked(self, identifier: str, blocked_dict: Dict[str, float], 
                   block_duration: int = 300) -> bool:
        """Verifica si un identificador está bloqueado"""
        if identifier in blocked_dict:
            if time.time() - blocked_dict[identifier] < block_duration:
                return True
            else:
                # Remover del bloqueo si ya expiró
                del blocked_dict[identifier]
        return False
    
    def check_rate_limit(
        self, 
        request: Request, 
        max_requests: int = None,
        window_seconds: int = 60,
        block_duration: int = 300
    ) -> Tuple[bool, Dict]:
        """
        Verifica si la request está dentro de los límites de velocidad configurados.
        
        Esta función implementa rate limiting por IP y por usuario autenticado.
        Los usuarios autenticados tienen límites más estrictos (mitad del límite por IP).
        
        Args:
            request: Objeto Request de FastAPI que contiene información de la petición
            max_requests: Máximo número de requests permitidas en la ventana de tiempo.
                         Si es None, usa el valor de configuración RATE_LIMIT_REQUESTS_PER_MINUTE
            window_seconds: Ventana de tiempo en segundos para contar requests (default: 60)
            block_duration: Duración del bloqueo en segundos cuando se excede el límite (default: 300)
        
        Returns:
            Tuple[bool, Dict]: 
                - bool: True si la request está permitida, False si está bloqueada
                - Dict: Información detallada del rate limiting:
                    - enabled: bool - Si el rate limiting está habilitado
                    - blocked: bool - Si el identificador está bloqueado
                    - exceeded: bool - Si se excedió el límite
                    - type: str - Tipo de límite ("ip" o "user")
                    - identifier: str - IP o ID de usuario
                    - requests: int - Número actual de requests
                    - limit: int - Límite configurado
                    - retry_after: int - Segundos antes de poder hacer nuevas requests
        
        Example:
            >>> is_allowed, info = rate_limiter.check_rate_limit(request)
            >>> if not is_allowed:
            ...     raise HTTPException(status_code=429, detail="Rate limit exceeded")
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, {"enabled": False}
        
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_identifier(request)
        
        # Usar límites de configuración si no se especifican
        if max_requests is None:
            max_requests = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        
        # Verificar si IP está bloqueada
        if self._is_blocked(client_ip, self.blocked_ips, block_duration):
            log_security_event("rate_limit_ip_blocked", details={"ip": client_ip})
            return False, {
                "blocked": True,
                "type": "ip",
                "identifier": client_ip,
                "retry_after": block_duration
            }
        
        # Verificar si usuario está bloqueado
        if user_id and self._is_blocked(user_id, self.blocked_users, block_duration):
            log_security_event("rate_limit_user_blocked", user_id=user_id)
            return False, {
                "blocked": True,
                "type": "user",
                "identifier": user_id,
                "retry_after": block_duration
            }
        
        # Verificar límites por IP
        ip_key = f"ip:{client_ip}"
        self._clean_old_requests(ip_key, window_seconds)
        
        if len(self.requests[ip_key]) >= max_requests:
            # Bloquear IP
            self.blocked_ips[client_ip] = time.time()
            log_security_event("rate_limit_ip_exceeded", details={
                "ip": client_ip,
                "requests": len(self.requests[ip_key]),
                "limit": max_requests
            })
            return False, {
                "exceeded": True,
                "type": "ip",
                "identifier": client_ip,
                "requests": len(self.requests[ip_key]),
                "limit": max_requests,
                "retry_after": block_duration
            }
        
        # Verificar límites por usuario (si está autenticado)
        if user_id:
            user_key = f"user:{user_id}"
            self._clean_old_requests(user_key, window_seconds)
            
            # Límite más estricto para usuarios autenticados
            user_max_requests = max_requests // 2
            
            if len(self.requests[user_key]) >= user_max_requests:
                # Bloquear usuario
                self.blocked_users[user_id] = time.time()
                log_security_event("rate_limit_user_exceeded", user_id=user_id, details={
                    "requests": len(self.requests[user_key]),
                    "limit": user_max_requests
                })
                return False, {
                    "exceeded": True,
                    "type": "user",
                    "identifier": user_id,
                    "requests": len(self.requests[user_key]),
                    "limit": user_max_requests,
                    "retry_after": block_duration
                }
        
        # Registrar la request actual
        current_time = time.time()
        self.requests[ip_key].append(current_time)
        if user_id:
            self.requests[f"user:{user_id}"].append(current_time)
        
        # Calcular información de rate limit
        remaining_requests = max_requests - len(self.requests[ip_key])
        reset_time = current_time + window_seconds
        
        return True, {
            "enabled": True,
            "remaining": remaining_requests,
            "limit": max_requests,
            "reset_time": reset_time,
            "window_seconds": window_seconds
        }


# Instancia global del rate limiter
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware de FastAPI para aplicar rate limiting
    
    Args:
        request: Request de FastAPI
        call_next: Función para continuar con el siguiente middleware
    
    Returns:
        Response de FastAPI
    """
    # Verificar si el rate limiting está habilitado
    if not settings.RATE_LIMIT_ENABLED:
        return await call_next(request)
    
    # Verificar rate limit
    is_allowed, rate_info = rate_limiter.check_rate_limit(request)
    
    if not is_allowed:
        # Si se excede el límite, retornar error 429
        error_detail = "Rate limit exceeded"
        if rate_info.get("blocked"):
            error_detail = "Access temporarily blocked"
        
        return JSONResponse(
            status_code=429,
            content={
                "detail": error_detail,
                "rate_limit_info": rate_info
            },
            headers={
                "Retry-After": str(rate_info.get("retry_after", 60)),
                "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(rate_info.get("reset_time", time.time() + 60)))
            }
        )
    
    # Continuar con la request
    response = await call_next(request)
    
    # Agregar headers de rate limit a la respuesta
    if rate_info.get("enabled"):
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(rate_info["reset_time"]))
    
    return response


def rate_limit_decorator(max_requests: int = None, window_seconds: int = 60):
    """
    Decorador para aplicar rate limiting a endpoints específicos
    
    Args:
        max_requests: Número máximo de requests por ventana
        window_seconds: Duración de la ventana en segundos
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Obtener el request del contexto
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Si no encontramos el request, continuar sin rate limiting
                return await func(*args, **kwargs)
            
            # Verificar rate limit
            is_allowed, rate_info = rate_limiter.check_rate_limit(
                request, max_requests, window_seconds
            )
            
            if not is_allowed:
                error_detail = "Rate limit exceeded for this endpoint"
                if rate_info.get("blocked"):
                    error_detail = "Access temporarily blocked"
                
                raise HTTPException(
                    status_code=429,
                    detail={
                        "detail": error_detail,
                        "rate_limit_info": rate_info
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_rate_limit_stats() -> Dict:
    """Obtiene estadísticas del rate limiting"""
    current_time = time.time()
    
    # Limpiar requests antiguos
    for key in list(rate_limiter.requests.keys()):
        rate_limiter._clean_old_requests(key)
    
    # Contar requests activos por tipo
    ip_requests = sum(1 for key in rate_limiter.requests if key.startswith("ip:"))
    user_requests = sum(1 for key in rate_limiter.requests if key.startswith("user:"))
    
    # Contar bloqueos activos
    active_ip_blocks = sum(1 for block_time in rate_limiter.blocked_ips.values() 
                          if current_time - block_time < 300)
    active_user_blocks = sum(1 for block_time in rate_limiter.blocked_users.values() 
                            if current_time - block_time < 300)
    
    return {
        "active_requests": {
            "ip_based": ip_requests,
            "user_based": user_requests,
            "total": ip_requests + user_requests
        },
        "active_blocks": {
            "ip_based": active_ip_blocks,
            "user_based": active_user_blocks,
            "total": active_ip_blocks + active_user_blocks
        },
        "total_blocked_ips": len(rate_limiter.blocked_ips),
        "total_blocked_users": len(rate_limiter.blocked_users),
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "default_limit": settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    }


def clear_rate_limit_data():
    """Limpia todos los datos de rate limiting (útil para testing)"""
    rate_limiter.requests.clear()
    rate_limiter.blocked_ips.clear()
    rate_limiter.blocked_users.clear()
    logger.info("Rate limit data cleared")
