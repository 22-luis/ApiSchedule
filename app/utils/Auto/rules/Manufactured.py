from typing import Dict, Any
from sqlalchemy.orm import Session

from app.services.utils.team_selection_service import TeamSelectionService
from app.core.enums import ManufacturingActivities
from app.services.config import ServiceType, ServiceConfig

class ManufacturedRule:
    
    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Dict[str, Any]:
        """
        Obtiene la actividad de fabricación específica para una orden.
        
        Args:
            order_data: Datos de la orden (lote, quantity, code)
            activities_data: Datos de actividades de fabricación con minutos calculados
            
        Returns:
            Actividad de fabricación específica para la orden o None si no se encuentra
        """
        order_code = order_data.get('code')
        if not order_code:
            return None
        
        code_data = activities_data.get("fabrication_activities_by_code", {}).get(order_code)
        
        if not code_data or not code_data.get("fabrication_activities"):
            return None
            
        fabrication_activities = code_data["fabrication_activities"]

        # Prioridad 1: Actividades de molienda
        molienda_keywords = [
            ManufacturingActivities.Mol_pasta.value.upper(),
            ManufacturingActivities.Mol_polvo.value.upper()
        ]
        for activity in fabrication_activities:
            activity_name = activity.get("activity", "").upper()
            if any(keyword in activity_name for keyword in molienda_keywords):
                return activity
                
        # Prioridad 2: Actividades de mezcla
        mezcla_keywords = [
            ManufacturingActivities.Mez_maquina.value.upper(),
            ManufacturingActivities.Mez_polvo.value.upper(),
            ManufacturingActivities.mez_liquida.value.upper()
        ]
        for activity in fabrication_activities:
            activity_name = activity.get("activity", "").upper()
            if any(keyword in activity_name for keyword in mezcla_keywords):
                return activity
                
        # Prioridad 3: Actividades de fabricación general
        fabricacion_keywords = [ManufacturingActivities.Fabricacion.value.upper()]
        for activity in fabrication_activities:
            activity_name = activity.get("activity", "").upper()
            if any(keyword in activity_name for keyword in fabricacion_keywords):
                return activity
        
        # Si no se encuentra ninguna actividad específica, usar la primera disponible
        if fabrication_activities:
            return fabrication_activities[0]
        
        return None

    def get_most_suitable_team(self, db: Session, order_data: Dict) -> Dict[str, Any]:
        """
        Determina el equipo de fabricación más adecuado según las reglas de negocio.
        
        Reglas:
        1. Fabricado 1: Códigos que inician con BX y la cantidad a producir es > 13.
        2. Fabricado 2: Aplican EXACTAMENTE las mismas condiciones que Fabricado 1.
        3. Fabricado 3: Códigos que inician con BX o BE y la cantidad a producir es < 13.
        4. Fabricado 3: Códigos de tipo M13.
        5. Molino: Códigos de tipo M9 y M10.
        
        Args:
            db: Sesión de base de datos
            order_data: Datos de la orden (lote, quantity, code)
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        code = order_data.get("code", "")
        quantity = order_data.get("quantity", 0)
        
        # Obtener todos los equipos de fabricación
        teams_data = TeamSelectionService.get_fabrication_teams(db)
        teams_by_type = teams_data.get("teams_by_type", {})
        
        # Reglas para Fabricado 1 y 2
        if code.startswith("BX") and quantity > 13:
            # Se intenta asignar a Fabricado 1, si no está disponible, a Fabricado 2
            fabricado1_team = teams_by_type.get("fabricado1")
            if fabricado1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": f"Código inicia con BX y cantidad > 13. Asignado a Fabricado 1.",
                    "rule_applied": "fabricado1_bx_gt_13"
                }
            
            fabricado2_team = teams_by_type.get("fabricado2")
            if fabricado2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado2_team.id),
                        "name": fabricado2_team.name,
                        "type": "fabricado2"
                    },
                    "reason": f"Código inicia con BX y cantidad > 13. Fabricado 1 no disponible, asignado a Fabricado 2.",
                    "rule_applied": "fabricado2_bx_gt_13"
                }

        # Reglas para Fabricado 3
        if ((code.startswith("BX") or code.startswith("BE")) and quantity < 13) or "M13" in code:
            fabricado3_team = teams_by_type.get("fabricado3")
            if fabricado3_team:
                reason = (
                    f"Código de tipo M13. Asignado a Fabricado 3."
                    if "M13" in code
                    else f"Código inicia con {code[:2]} y cantidad < 13. Asignado a Fabricado 3."
                )
                rule = "fabricado3_m13" if "M13" in code else "fabricado3_bx_be_lt_13"
                
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": reason,
                    "rule_applied": rule
                }
        
        # Reglas para Molino
        if "M9" in code or "M10" in code:
            molino_team = teams_by_type.get("molino")
            if molino_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(molino_team.id),
                        "name": molino_team.name,
                        "type": "molino"
                    },
                    "reason": f"Código de tipo {code[:3]}. Asignado a Molino.",
                    "rule_applied": "molino_m9_m10"
                }

        # Fallback si no se cumple ninguna regla específica
        return {
            "success": False,
            "reason": "No se encontró un equipo de fabricación adecuado según las reglas para la orden.",
            "rule_applied": "no_rule_matched"
        }

