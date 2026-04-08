from typing import Dict, Any, Optional, List, Set
from abc import ABC, abstractmethod
from app.modules.automation.services.config import ServiceType, ServiceConfig
from sqlalchemy.orm import Session
from app.modules.codes.models.code import Code
from app.modules.codes.models.code_automation_rule import CodeAutomationRule

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

    @staticmethod
    def is_liquid_product(order_data: dict) -> bool:
        """
        Determina si un producto es líquido basado en su descripción o unidad.
        Regla Global: JARABE, ESEM, ESENCIA, DESINFECTANTE SOLUCIÓN, LIQUIDO o unidad GL/LT
        """
        description = order_data.get("description", "").upper()
        unit = order_data.get("unit", "").upper()

        liquid_keywords = ["JARABE", "ESEM", "ESENCIA", "DESINFECTANTE SOLUCIÓN", "LIQUIDO"]

        return any(k in description for k in liquid_keywords) or unit in ["GL", "LT"]

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
                # Para Packaging: excluir manufactured -> check inclusion or keywords.
                
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

    @staticmethod
    def response(team_id, name, type_, reason, rule):
        return {
            "success": True,
            "selected_team": {
                "id": str(team_id),
                "name": name,
                "type": type_
            },
            "reason": reason,
            "rule_applied": rule
        }

    def check_db_rules(self, db: Session, order_data: Dict, activity_type: Optional[str]) -> Optional[Dict[str, Any]]:
        code_str = order_data.get("code", "")
        quantity = order_data.get("quantity", 0)

        if not code_str:
            return None

        # Fetch the code object
        code_obj = db.query(Code).filter(Code.code == code_str).first()
        if not code_obj:
            return None

        # Fetch rules for this code and service type
        rules = db.query(CodeAutomationRule).filter(
            CodeAutomationRule.code_id == code_obj.id,
            CodeAutomationRule.service_type == self.service_type.value
        ).order_by(CodeAutomationRule.priority.asc()).all()

        for rule in rules:
            # Check activity type if rule specifies one
            if rule.activity_type and rule.activity_type != activity_type:
                continue

            # Check min quantity
            if rule.min_quantity is not None and quantity < rule.min_quantity:
                continue

            # Check max quantity
            if rule.max_quantity is not None and quantity > rule.max_quantity:
                continue

            # Match! 
            target_team = rule.target_team
            overflow_team = rule.overflow_team

            # We can check capacity if needed, but for now we just return target or overflow
            from app.modules.automation.services.utils.capacity_verification_service import CapacityVerificationService
            # Check capacity 
            # Note: capacity logic in get_most_suitable_team receives programming_date, but here we don't have it explicitly.
            # Base response 
            return {
                "success": True,
                "selected_team": {
                    "id": str(target_team.id),
                    "name": target_team.name,
                    "type": target_team.name.lower()
                },
                "overflow_team": {
                    "id": str(overflow_team.id),
                    "name": overflow_team.name,
                    "type": overflow_team.name.lower()
                } if overflow_team else None,
                "reason": f"Regla de BD aplicada (Prioridad {rule.priority})",
                "rule_applied": f"db_rule_{rule.id}"
            }
        
        return None
