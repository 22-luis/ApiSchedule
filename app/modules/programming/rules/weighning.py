from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.modules.programming.services.utils.team_selection_service import TeamSelectionService
from app.modules.programming.services.config import ServiceType, ServiceConfig

class WeighingRule:
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra las actividades para obtener solo las relacionadas con pesado para códigos M7.
        
        Args:
            activities_data: Diccionario con todas las actividades organizadas por código
            
        Returns:
            Diccionario con solo las actividades de pesado organizadas por código
        """
        weighing_activities_by_code = {}
        
        activities_by_code = activities_data.get("activities_by_code", {})
        for code, code_data in activities_by_code.items():
            activities = code_data.get("activities", [])
            weighing_activities = []
            
            for activity in activities:
                activity_name = activity.get("activity", "").upper()
                
                # Buscar actividades relacionadas con pesado usando configuración centralizada
                weighing_keywords = ServiceConfig.get_activity_keywords(ServiceType.WEIGHING)
                if any(keyword in activity_name for keyword in weighing_keywords):
                    weighing_activities.append(activity)
            
            if weighing_activities:
                weighing_activities_by_code[code] = {
                    "code": code,
                    "weighing_activities": weighing_activities,
                    "total_weighing_activities": len(weighing_activities),
                    "found": True
                }
        
        return {
            "weighing_activities_by_code": weighing_activities_by_code,
            "total_codes_with_weighing": len(weighing_activities_by_code),
            "codes_with_weighing": list(weighing_activities_by_code.keys())
        }

    def get_most_suitable_team(self, db: Session, order_data: Dict = None, activity_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene el equipo de pesado según las reglas del flujograma.
        
        Reglas:
        - M7: PESADO (función principal de pesado y/o fabricado)
        - M12: PESADO (mezcla en máquina/empaque 25 kg, lotes grandes ~400 unidades)
        
        Args:
            db: Sesión de base de datos
            order_data: Datos de la orden (opcional)
            activity_type: Tipo de actividad (M7, M12)
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        team_info = TeamSelectionService.get_weighing_team(db)
        
        if team_info.get("success"):
            # Determinar la razón según el tipo de actividad
            if activity_type == "M7":
                team_info["reason"] = "Actividad M7 (Pesado y/o Fabricado). Asignado a PESADO."
                team_info["rule_applied"] = "pesado_m7"
            elif activity_type == "M12":
                team_info["reason"] = "Actividad M12 (Mezcla en Máquina/Empaque 25 Kg, lotes grandes). Asignado a PESADO."
                team_info["rule_applied"] = "pesado_m12"
            else:
                # Fallback para actividades de pesado sin tipo específico
                team_info["reason"] = "Actividad de pesado. Asignado a PESADO."
                team_info["rule_applied"] = "pesado_default"
        
        return team_info

    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Dict[str, Any]:
        """
        Obtiene la actividad de pesado específica para una orden.
        
        Args:
            order_data: Datos de la orden (lote, quantity, code)
            activities_data: Datos de actividades de pesado con minutos calculados
            
        Returns:
            Actividad de pesado específica para la orden o None si no se encuentra
        """
        order_code = order_data.get('code')
        if not order_code:
            return None
        
        # Buscar las actividades para el código de esta orden
        code_data = activities_data.get("weighing_activities_by_code", {}).get(order_code)
        
        if not code_data or not code_data.get("weighing_activities"):
            return None
        
        # Buscar específicamente la actividad "PESADO"
        pesado_activity = None
        for activity in code_data["weighing_activities"]:
            activity_name = activity.get("activity", "")
            if activity_name and "PESADO" in activity_name.upper():
                pesado_activity = activity
                break
        
        # Si no se encuentra "PESADO", usar la primera actividad disponible
        if not pesado_activity:
            pesado_activity = code_data["weighing_activities"][0]
        
        return pesado_activity
