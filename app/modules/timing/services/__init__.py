from .operator_timer_service import TimerService
from .supervisor_timer_service import SupTimerService

# Para mantener compatibilidad con algunos imports que buscaban 'timer_service' directamente
timer_service = TimerService
