"""
Factory para crear instancias de servicios de tareas.
Facilita la creación de servicios según el tipo requerido.
"""

from typing import Optional
from app.services.config import ServiceType
from app.services.weighing_task_service_refactored import WeighingTaskService
from app.services.fabrication_task_service_refactored import FabricationTaskService
from app.services.base_task_service import BaseTaskService


class TaskServiceFactory:
    """Factory para crear servicios de tareas"""
    
    @staticmethod
    def create_service(service_type: ServiceType) -> Optional[BaseTaskService]:
        """
        Crea una instancia del servicio especificado.
        
        Args:
            service_type: Tipo de servicio a crear
            
        Returns:
            Instancia del servicio o None si el tipo no es válido
        """
        if service_type == ServiceType.WEIGHING:
            return WeighingTaskService()
        elif service_type == ServiceType.FABRICATION:
            return FabricationTaskService()
        elif service_type == ServiceType.PACKAGING:
            # TODO: Implementar cuando se cree el servicio de empaque
            return None
        else:
            return None
    
    @staticmethod
    def create_weighing_service() -> WeighingTaskService:
        """
        Crea una instancia del servicio de pesado.
        
        Returns:
            Instancia del servicio de pesado
        """
        return WeighingTaskService()
    
    @staticmethod
    def create_fabrication_service() -> FabricationTaskService:
        """
        Crea una instancia del servicio de fabricación.
        
        Returns:
            Instancia del servicio de fabricación
        """
        return FabricationTaskService()
    
    @staticmethod
    def get_available_services() -> list:
        """
        Obtiene la lista de servicios disponibles.
        
        Returns:
            Lista de tipos de servicios disponibles
        """
        return [
            ServiceType.WEIGHING,
            ServiceType.FABRICATION
            # ServiceType.PACKAGING  # Descomentar cuando se implemente
        ]
    
    @staticmethod
    def get_service_info(service_type: ServiceType) -> dict:
        """
        Obtiene información sobre un tipo de servicio.
        
        Args:
            service_type: Tipo de servicio
            
        Returns:
            Información del servicio
        """
        from app.services.config import ServiceConfig
        
        config = ServiceConfig.get_config(service_type)
        return {
            "type": service_type.value,
            "description": config.get("description", "Servicio no configurado"),
            "time_limit": config.get("time_limit", "No definido"),
            "tolerance_minutes": config.get("tolerance_minutes", 0),
            "available": TaskServiceFactory.create_service(service_type) is not None
        }
