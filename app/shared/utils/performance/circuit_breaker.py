"""
Sistema de Circuit Breaker para proteger contra fallos en servicios externos.
Implementa el patrón Circuit Breaker para mejorar la resiliencia de la aplicación.
"""
import time
import asyncio
from typing import Any, Callable, Dict
from enum import Enum
from functools import wraps
from app.shared.utils.core.logging import get_logger

logger = get_logger("circuit_breaker")


class CircuitState(Enum):
    """Estados del circuit breaker"""
    CLOSED = "CLOSED"      # Funcionando normalmente
    OPEN = "OPEN"          # Bloqueado por fallos
    HALF_OPEN = "HALF_OPEN"  # Probando si el servicio se recuperó

# Protege contra fallos en cascada cuando un servicio externo falla.
class CircuitBreaker:
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold #Número de fallos antes de abrir el circuito
        self.recovery_timeout = recovery_timeout #Tiempo en segundos antes de intentar recuperación
        self.expected_exception = expected_exception #Tipo de excepción que se considera fallo
        self.name = name #Nombre del circuit breaker para logging
        
        self.state = CircuitState.CLOSED #Estado del circuit breaker
        self.failure_count = 0 #Contador de fallos
        self.last_failure_time = None #Tiempo de último fallo
        self.success_count = 0 #Contador de éxitos
        
        logger.info(f"Circuit breaker '{name}' inicializado")
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._execute_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._execute_sync(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    async def _execute_async(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._set_half_open()
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' está abierto. "
                    f"Último fallo: {self.last_failure_time}"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            logger.warning(
                f"Circuit breaker '{self.name}' fallo #{self.failure_count}: {str(e)}"
            )
            raise
    
    def _execute_sync(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._set_half_open()
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' está abierto. "
                    f"Último fallo: {self.last_failure_time}"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            logger.warning(
                f"Circuit breaker '{self.name}' fallo #{self.failure_count}: {str(e)}"
            )
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Determina si se debe intentar resetear el circuito"""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _set_half_open(self):
        self.state = CircuitState.HALF_OPEN
        logger.info(f"Circuit breaker '{self.name}' cambiado a HALF_OPEN")
    
    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self._reset()
        else:
            self.success_count += 1
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self._open()
        elif self.failure_count >= self.failure_threshold:
            self._open()
    
    def _open(self):
        self.state = CircuitState.OPEN
        logger.error(
            f"Circuit breaker '{self.name}' abierto después de {self.failure_count} fallos"
        )
    
    def _reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' reseteado")
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class CircuitBreakerOpenError(Exception):
    """Excepción lanzada cuando el circuit breaker está abierto"""
    pass


# Circuit breakers predefinidos para servicios comunes
class CircuitBreakers:
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    # Obtiene o crea un circuit breaker.
    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ) -> CircuitBreaker:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                name=name
            )
        
        return self.breakers[name]
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: breaker.get_status()
            for name, breaker in self.breakers.items()
        }
    
    def reset_all(self):
        for breaker in self.breakers.values():
            breaker._reset()


# Instancia global de circuit breakers
circuit_breakers = CircuitBreakers()


# Circuit breaker para operaciones de base de datos
def database_circuit_breaker(func: Callable) -> Callable:
    breaker = circuit_breakers.get_breaker(
        name="database",
        failure_threshold=3,
        recovery_timeout=30,
        expected_exception=Exception
    )
    return breaker(func)

# Circuit breaker para APIs externas
def external_api_circuit_breaker(func: Callable) -> Callable:
    breaker = circuit_breakers.get_breaker(
        name="external_api",
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=Exception
    )
    return breaker(func)


# Ejemplo de uso:
"""
@database_circuit_breaker
async def get_user_from_db(user_id: str):
    # Operación de base de datos
    pass

@external_api_circuit_breaker
async def call_external_api():
    # Llamada a API externa
    pass
"""
