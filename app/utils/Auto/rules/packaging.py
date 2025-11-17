from typing import Dict, Any
from sqlalchemy.orm import Session

from app.services.utils.team_selection_service import TeamSelectionService
from app.core.enums import PackagingActivities
from app.services.config import ServiceType, ServiceConfig

class PackagingRule:
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra las actividades para obtener solo las relacionadas con empaque.
        
        Args:
            activities_data: Diccionario con todas las actividades organizadas por código
            
        Returns:
            Diccionario con solo las actividades de empaque organizadas por código
        """
        packaging_activities_by_code = {}
        
        activities_by_code = activities_data.get("activities_by_code", {})
        for code, code_data in activities_by_code.items():
            activities = code_data.get("activities", [])
            packaging_activities = []
            
            for activity in activities:
                activity_name = activity.get("activity", "").upper()
                
                # Buscar actividades relacionadas con empaque usando configuración centralizada
                packaging_keywords = ServiceConfig.get_activity_keywords(ServiceType.PACKAGING)
                if any(keyword in activity_name for keyword in packaging_keywords):
                    packaging_activities.append(activity)
            
            if packaging_activities:
                packaging_activities_by_code[code] = {
                    "code": code,
                    "packaging_activities": packaging_activities,
                    "total_packaging_activities": len(packaging_activities),
                    "found": True
                }
        
        return {
            "packaging_activities_by_code": packaging_activities_by_code,
            "total_codes_with_packaging": len(packaging_activities_by_code),
            "codes_with_packaging": list(packaging_activities_by_code.keys())
        }

    def get_most_suitable_team(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de empaque disponibles.
        Como las actividades de empaque requieren selección específica por actividad,
        este método devuelve todos los equipos disponibles para que se seleccione el apropiado.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información de todos los equipos de empaque
        """
        return TeamSelectionService.get_packaging_teams(db)

    def get_packaging_teams(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de empaque.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información de todos los equipos de empaque
        """
        return TeamSelectionService.get_packaging_teams(db)

    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Dict[str, Any]:
        """
        Obtiene la actividad de empaque específica para una orden.
        
        Args:
            order_data: Datos de la orden (lote, quantity, code)
            activities_data: Datos de actividades de empaque con minutos calculados
            
        Returns:
            Actividad de empaque específica para la orden o None si no se encuentra
        """
        order_code = order_data.get('code')
        if not order_code:
            return None
        
        # Buscar las actividades para el código de esta orden
        code_data = activities_data.get("packaging_activities_by_code", {}).get(order_code)
        
        if not code_data or not code_data.get("packaging_activities"):
            return None
        
        # Buscar la actividad más específica según prioridad
        packaging_activities = code_data["packaging_activities"]
        
        # Prioridad 1: Empaque manual grupo
        grupo_activities = [PackagingActivities.Emp_grupo.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(grupo_activity.upper() in activity_name for grupo_activity in grupo_activities):
                return activity
        
        # Prioridad 2: Empaque manual
        manual_activities = [PackagingActivities.Emp_manual.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(manual_activity.upper() in activity_name for manual_activity in manual_activities):
                return activity
        
        # Prioridad 3: Empaque máquina semi-automática
        semi_activities = [PackagingActivities.Emp_semi.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(semi_activity.upper() in activity_name for semi_activity in semi_activities):
                return activity
        
        # Prioridad 4: Empaque máquina automática
        auto_activities = [PackagingActivities.Emp_auto.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(auto_activity.upper() in activity_name for auto_activity in auto_activities):
                return activity
        
        # Prioridad 5: Empaque manual con mezcla
        mezcla_activities = [PackagingActivities.Emp_mezcla.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(mezcla_activity.upper() in activity_name for mezcla_activity in mezcla_activities):
                return activity
        
        # Si no se encuentra ninguna actividad específica, usar la primera disponible
        if packaging_activities:
            return packaging_activities[0]
        
        return None

    def get_specific_team_for_activity(self, activity_name: str, activity_description: str, teams_data: Dict) -> Dict[str, Any]:
        """
        Obtiene el equipo específico para una actividad de empaque según las reglas de negocio.
        
        Args:
            activity_name: Nombre de la actividad
            activity_description: Descripción de la actividad
            teams_data: Datos de equipos obtenidos de get_most_suitable_team
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        return TeamSelectionService.get_specific_packaging_team_for_activity(
            activity_name, activity_description, teams_data
        )
