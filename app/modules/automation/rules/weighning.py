from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.modules.automation.services.utils.team_selection_service import TeamSelectionService
from app.modules.automation.services.config import ServiceType, ServiceConfig
from app.modules.automation.rules.base_rule import BaseAutomationRule

class WeighingRule(BaseAutomationRule):
    
    @property
    def service_type(self) -> ServiceType:
        return ServiceType.WEIGHING

    @property
    def activity_list_key(self) -> str:
        return "weighing_activities"

    @property
    def priority_keywords_groups(self) -> List[List[str]]:
        return [["PESADO"]]

    def get_most_suitable_team(self, db: Session, order_data: Dict = None, activity_type: Optional[str] = None) -> Dict[str, Any]:
        # Restriction removed: Weighing tasks should be created regardless of quantity.
        pass

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
