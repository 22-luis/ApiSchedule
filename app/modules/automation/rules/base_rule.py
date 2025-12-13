from typing import Dict, Any, Optional, List, Set, Union
from abc import ABC, abstractmethod
from app.modules.automation.services.config import ServiceType, ServiceConfig

class BaseAutomationRule(ABC):
    
    @property
    @abstractmethod
    def service_type(self) -> ServiceType:
        pass

    @property
    @abstractmethod
    def activity_list_key(self) -> str:
        pass

    @property
    def excluded_types(self) -> Set[str]:
        return set()

    @property
    def allowed_types(self) -> Set[str]:
        return set()

    @property
    def priority_keywords_groups(self) -> List[List[str]]:
        return []

    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        filtered_activities_by_code = {}
        
        activities_by_code = activities_data.get("activities_by_code", {})
        service_keywords = ServiceConfig.get_activity_keywords(self.service_type)

        for code, code_data in activities_by_code.items():
            activities = code_data.get("activities", [])
            relevant_activities = []
            
            for activity in activities:
                activity_type = activity.get("type")
                activity_name = activity.get("activity", "").upper()

                # 1. Chequear exclusiones explícitas
                if activity_type in self.excluded_types:
                    continue

                # 2. Chequear inclusiones explícitas (Whitelisting o coincidencia de keywords)
                # Si activity_type está en allowed_types, lo incluimos.
                # Si NO está en allowed_types, pero coincide con keywords, también lo incluimos.
                # (Esta lógica replica lo visto en packaging.py: if (type in allowed) or (keyword match))
                
                is_allowed_type = activity_type in self.allowed_types
                matches_keyword = any(keyword in activity_name for keyword in service_keywords)

                # Para Manufactured, la lógica era: excluir M1/M7 -> luego check keywords.
                # Para Weighing: check keywords.
                # Para Packaging: excluir manf -> check inclusion or keywords.
                
                # Unificamos:
                # Si hay allowed_types definido, se usa como condición OR con matches_keyword.
                # Si allowed_types está vacío (ej. Weighing/Manufactured), solo depende de matches_keyword.
                
                should_include = False
                if self.allowed_types and is_allowed_type:
                    should_include = True
                elif matches_keyword:
                    should_include = True
                
                if should_include:
                    relevant_activities.append(activity)
            
            if relevant_activities:
                filtered_activities_by_code[code] = {
                    "code": code,
                    self.activity_list_key: relevant_activities,
                    f"total_{self.activity_list_key}": len(relevant_activities),
                    "found": True
                }
        
        return {
            f"{self.activity_list_key}_by_code": filtered_activities_by_code,
            f"total_codes_with_{self.activity_list_key.split('_')[0]}": len(filtered_activities_by_code),
            f"codes_with_{self.activity_list_key.split('_')[0]}": list(filtered_activities_by_code.keys())
        }

    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict[str, Any]]:
        order_code = order_data.get('code')
        if not order_code:
            return None
        
        # Obtener datos usando la clave dinámica
        code_data = activities_data.get(f"{self.activity_list_key}_by_code", {}).get(order_code)
        
        if not code_data or not code_data.get(self.activity_list_key):
            return None
        
        activities_list = code_data[self.activity_list_key]
        
        # Iterar sobre los grupos de prioridad
        if self.priority_keywords_groups:
            for keywords_group in self.priority_keywords_groups:
                # Normalizar keywords del grupo a mayúsculas
                upper_keywords = [k.upper() for k in keywords_group]
                
                for activity in activities_list:
                    activity_name = activity.get("activity", "").upper()
                    if any(keyword in activity_name for keyword in upper_keywords):
                        return activity
        
        # Fallback: Si no se encuentra ninguna específica o no hay grupos de prioridad,
        # devolver la primera disponible.
        if activities_list:
            return activities_list[0]
        
        return None

    def response(self, team_id, name, type, reason, rule):
        return {
            "success": True,
            "selected_team": {
                "id": str(team_id),
                "name": name,
                "type": type
            },
            "reason": reason,
            "rule_applied": rule
        }
