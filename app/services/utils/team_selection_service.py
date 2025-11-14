"""
Servicio para selección de equipos según reglas de negocio.
Separa la lógica compleja de selección de equipos de los servicios principales.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.team import Team
from app.core.enums import ManufacturingActivities, ManufacturingTeams, PackagingActivities, PackagingTeams


class TeamSelectionService:
    """Servicio para selección de equipos según reglas de negocio"""
    
    @staticmethod
    def get_weighing_team(db: Session) -> Dict[str, Any]:
        """
        Obtiene el equipo más idóneo para actividades de pesado.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información del equipo más idóneo para pesado
        """
        # Buscar equipos que contengan "pesado" en el nombre
        weighing_teams = db.query(Team).filter(Team.name.ilike('%pesado%')).all()
        
        if not weighing_teams:
            return {
                "success": False,
                "message": "No se encontraron equipos de pesado en la base de datos",
                "weighing_teams": [],
                "most_suitable_team": None
            }
        
        # Lógica para determinar el equipo más idóneo
        most_suitable_team = None
        
        # Buscar "pesado principal"
        for team in weighing_teams:
            if "principal" in team.name.lower():
                most_suitable_team = team
                break
        
        # Si no hay principal, buscar "pesado 1"
        if not most_suitable_team:
            for team in weighing_teams:
                if "pesado 1" in team.name.lower() or "pesado1" in team.name.lower():
                    most_suitable_team = team
                    break
        
        # Si no hay ninguno específico, tomar el primero
        if not most_suitable_team and weighing_teams:
            most_suitable_team = weighing_teams[0]
        
        if most_suitable_team:
            return {
                "success": True,
                "message": f"Equipo más idóneo para pesado encontrado: {most_suitable_team.name}",
                "weighing_teams": [
                    {
                        "id": str(team.id),
                        "name": team.name,
                        "is_most_suitable": team.id == most_suitable_team.id
                    } for team in weighing_teams
                ],
                "most_suitable_team": {
                    "id": str(most_suitable_team.id),
                    "name": most_suitable_team.name,
                    "supervisor_id": str(most_suitable_team.supervisorId) if most_suitable_team.supervisorId else None
                },
                "total_weighing_teams": len(weighing_teams)
            }
        else:
            return {
                "success": False,
                "message": "No se pudo determinar el equipo más idóneo para pesado",
                "weighing_teams": [],
                "most_suitable_team": None
            }
    
    @staticmethod
    def get_fabrication_teams(db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de fabricación disponibles.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información de todos los equipos de fabricación
        """
        # Usar los equipos definidos en ManufacturingTeams
        manufacturing_team_names = [
            ManufacturingTeams.FABRICADO1.value,
            ManufacturingTeams.FABRICADO2.value,
            ManufacturingTeams.FABRICADO3.value,
            ManufacturingTeams.Molino.value
        ]
        
        fabrication_teams = []
        
        # Buscar equipos que coincidan con los nombres definidos en ManufacturingTeams
        for team_name in manufacturing_team_names:
            teams = db.query(Team).filter(Team.name.ilike(f'%{team_name}%')).all()
            fabrication_teams.extend(teams)
        
        # Si no se encuentran equipos específicos, buscar por palabras clave
        if not fabrication_teams:
            # Buscar equipos que contengan "fabricado" en el nombre
            fabrication_teams = db.query(Team).filter(Team.name.ilike('%fabricado%')).all()
        
        if not fabrication_teams:
            # Si no hay equipos con "fabricado", buscar equipos de molino
            fabrication_teams = db.query(Team).filter(Team.name.ilike('%molino%')).all()
        
        if not fabrication_teams:
            # Si no hay equipos de molino, buscar equipos de fabricación
            fabrication_teams = db.query(Team).filter(Team.name.ilike('%fabricacion%')).all()
        
        if not fabrication_teams:
            return {
                "success": False,
                "message": "No se encontraron equipos de fabricación en la base de datos",
                "fabrication_teams": [],
                "most_suitable_team": None
            }
        
        # Organizar equipos por tipo
        molino_teams = []
        fabricado1_teams = []
        fabricado2_teams = []
        fabricado3_teams = []
        
        for team in fabrication_teams:
            team_name_lower = team.name.lower()
            if ManufacturingTeams.Molino.value.lower() in team_name_lower:
                molino_teams.append(team)
            elif ManufacturingTeams.FABRICADO1.value.lower() in team_name_lower:
                fabricado1_teams.append(team)
            elif ManufacturingTeams.FABRICADO2.value.lower() in team_name_lower:
                fabricado2_teams.append(team)
            elif ManufacturingTeams.FABRICADO3.value.lower() in team_name_lower:
                fabricado3_teams.append(team)
        
        # Tomar el primer equipo de cada tipo como representante
        molino_team = molino_teams[0] if molino_teams else None
        fabricado1_team = fabricado1_teams[0] if fabricado1_teams else None
        fabricado2_team = fabricado2_teams[0] if fabricado2_teams else None
        fabricado3_team = fabricado3_teams[0] if fabricado3_teams else None
        
        return {
            "success": True,
            "message": f"Equipos de fabricación encontrados: {len(fabrication_teams)} equipos",
            "fabrication_teams": [
                {
                    "id": str(team.id),
                    "name": team.name,
                    "type": "molino" if ManufacturingTeams.Molino.value.lower() in team.name.lower() else
                           "fabricado1" if ManufacturingTeams.FABRICADO1.value.lower() in team.name.lower() else
                           "fabricado2" if ManufacturingTeams.FABRICADO2.value.lower() in team.name.lower() else
                           "fabricado3" if ManufacturingTeams.FABRICADO3.value.lower() in team.name.lower() else "otro"
                } for team in fabrication_teams
            ],
            "teams_by_type": {
                "molino": molino_team,
                "fabricado1": fabricado1_team,
                "fabricado2": fabricado2_team,
                "fabricado3": fabricado3_team
            },
            "total_fabrication_teams": len(fabrication_teams)
        }
    
    @staticmethod
    def get_specific_fabrication_team_for_activity(activity_name: str, activity_description: str, teams_data: Dict) -> Dict[str, Any]:
        """
        Determina el equipo específico para una actividad de fabricación según las reglas de negocio.
        
        Reglas:
        1. Molino: Actividades que contengan "MOLIENDA"
        2. Fabricado 2: Descripción que contenga "esencia" O actividad "MEZCLA LIQUIDA"
        3. Fabricado 1: Actividades "MEZCLA EN MAQUINA" o "MEZCLA MANUAL POLVO"
        4. Fabricado 3: Actividades "FABRICACION" con "ADEREZOS" o "JALEAS"
        
        Args:
            activity_name: Nombre de la actividad
            activity_description: Descripción de la actividad
            teams_data: Datos de equipos obtenidos de get_fabrication_teams
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        activity_upper = activity_name.upper() if activity_name else ""
        description_lower = activity_description.lower() if activity_description else ""
        
        teams_by_type = teams_data.get("teams_by_type", {})
        
        # Regla 1: Molino para actividades de molienda
        molienda_activities = [
            ManufacturingActivities.Mol_pasta.value,
            ManufacturingActivities.Mol_polvo.value
        ]
        
        if any(molienda_activity in activity_upper for molienda_activity in molienda_activities):
            molino_team = teams_by_type.get("molino")
            if molino_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(molino_team.id),
                        "name": molino_team.name,
                        "type": "molino"
                    },
                    "reason": f"Actividad de molienda: {activity_name}",
                    "rule_applied": "molienda"
                }
        
        # Regla 2: Fabricado 2 para descripciones con "esencia" O actividad "MEZCLA LIQUIDA"
        if ("esencia" in description_lower or 
            ManufacturingActivities.mez_liquida.value.upper() in activity_upper):
            fabricado2_team = teams_by_type.get("fabricado2")
            if fabricado2_team:
                reason = ""
                if "esencia" in description_lower:
                    reason = f"Descripción contiene 'esencia': {activity_description}"
                else:
                    reason = f"Actividad de mezcla líquida: {activity_name}"
                
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado2_team.id),
                        "name": fabricado2_team.name,
                        "type": "fabricado2"
                    },
                    "reason": reason,
                    "rule_applied": "esencia_o_mezcla_liquida"
                }
        
        # Regla 3: Fabricado 1 para actividades "MEZCLA EN MAQUINA" o "MEZCLA MANUAL POLVO"
        mezcla_activities = [
            ManufacturingActivities.Mez_maquina.value,
            ManufacturingActivities.Mez_polvo.value
        ]
        
        if any(mezcla_activity.upper() in activity_upper for mezcla_activity in mezcla_activities):
            fabricado1_team = teams_by_type.get("fabricado1")
            if fabricado1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": f"Actividad de mezcla: {activity_name}",
                    "rule_applied": "mezcla_fabricado1"
                }
        
        # Regla 4: Fabricado 3 para actividades "FABRICACION" con "ADEREZOS" o "JALEAS"
        if (ManufacturingActivities.Fabricacion.value.upper() in activity_upper and
            ("ADEREZOS" in activity_upper or "JALEAS" in activity_upper or 
             "aderezos" in description_lower or "jaleas" in description_lower)):
            fabricado3_team = teams_by_type.get("fabricado3")
            if fabricado3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": f"Fabricación de aderezos/jaleas: {activity_name}",
                    "rule_applied": "fabricacion_aderezos_jaleas"
                }
        
        # Regla 5: Distribuir entre Fabricado 1 y 3 para las demás tareas
        fabricado1_team = teams_by_type.get("fabricado1")
        fabricado3_team = teams_by_type.get("fabricado3")
        
        # Lógica simple de distribución: alternar entre Fabricado 1 y 3
        # Usar un contador estático para alternar
        if not hasattr(TeamSelectionService, '_distribution_counter'):
            TeamSelectionService._distribution_counter = 0
        
        TeamSelectionService._distribution_counter += 1
        
        if TeamSelectionService._distribution_counter % 2 == 1:
            # Impar: usar Fabricado 1
            if fabricado1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": f"Distribución automática: Fabricado 1 (tarea #{TeamSelectionService._distribution_counter})",
                    "rule_applied": "distribucion_fabricado1"
                }
        else:
            # Par: usar Fabricado 3
            if fabricado3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": f"Distribución automática: Fabricado 3 (tarea #{TeamSelectionService._distribution_counter})",
                    "rule_applied": "distribucion_fabricado3"
                }
        
        # Si no se puede aplicar ninguna regla, usar el primer equipo disponible
        available_teams = [fabricado1_team, fabricado3_team, teams_by_type.get("fabricado2"), teams_by_type.get("molino")]
        for team in available_teams:
            if team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(team.id),
                        "name": team.name,
                        "type": "fallback"
                    },
                    "reason": f"Equipo de respaldo: {team.name}",
                    "rule_applied": "fallback"
                }
        
        return {
            "success": False,
            "selected_team": None,
            "reason": "No se encontró equipo disponible para la actividad",
            "rule_applied": "none"
        }

    @staticmethod
    def get_packaging_teams(db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de empaque disponibles.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información de todos los equipos de empaque
        """
        # Usar los equipos definidos en PackagingTeams
        packaging_team_names = [
            PackagingTeams.EMPAQUE1.value,
            PackagingTeams.EMPAQUE2.value,
            PackagingTeams.EMPAQUE3.value,
            PackagingTeams.EMPAQUE4.value,
            PackagingTeams.MAQUINA1.value,
            PackagingTeams.MAQUINA2.value
        ]
        
        packaging_teams = []
        
        # Buscar equipos que coincidan con los nombres definidos en PackagingTeams
        for team_name in packaging_team_names:
            teams = db.query(Team).filter(Team.name.ilike(f'%{team_name}%')).all()
            packaging_teams.extend(teams)
        
        # Si no se encuentran equipos específicos, buscar por palabras clave
        if not packaging_teams:
            # Buscar equipos que contengan "empaque" en el nombre
            packaging_teams = db.query(Team).filter(Team.name.ilike('%empaque%')).all()
        
        if not packaging_teams:
            # Si no hay equipos con "empaque", buscar equipos de máquina
            packaging_teams = db.query(Team).filter(Team.name.ilike('%maquina%')).all()
        
        if not packaging_teams:
            return {
                "success": False,
                "message": "No se encontraron equipos de empaque en la base de datos",
                "packaging_teams": [],
                "most_suitable_team": None
            }
        
        # Organizar equipos por tipo
        empaque_teams = []
        empaque2_teams = []
        empaque3_teams = []
        empaque4_teams = []
        maquina1_teams = []
        maquina2_teams = []
        
        for team in packaging_teams:
            team_name_lower = team.name.lower()
            if PackagingTeams.EMPAQUE1.value.lower() in team_name_lower:
                empaque_teams.append(team)
            elif PackagingTeams.EMPAQUE2.value.lower() in team_name_lower:
                empaque2_teams.append(team)
            elif PackagingTeams.EMPAQUE3.value.lower() in team_name_lower:
                empaque3_teams.append(team)
            elif PackagingTeams.EMPAQUE4.value.lower() in team_name_lower:
                empaque4_teams.append(team)
            elif PackagingTeams.MAQUINA1.value.lower() in team_name_lower:
                maquina1_teams.append(team)
            elif PackagingTeams.MAQUINA2.value.lower() in team_name_lower:
                maquina2_teams.append(team)
        
        # Tomar el primer equipo de cada tipo como representante
        empaque_team = empaque_teams[0] if empaque_teams else None
        empaque2_team = empaque2_teams[0] if empaque2_teams else None
        empaque3_team = empaque3_teams[0] if empaque3_teams else None
        empaque4_team = empaque4_teams[0] if empaque4_teams else None
        maquina1_team = maquina1_teams[0] if maquina1_teams else None
        maquina2_team = maquina2_teams[0] if maquina2_teams else None
        
        return {
            "success": True,
            "message": f"Equipos de empaque encontrados: {len(packaging_teams)} equipos",
            "packaging_teams": [
                {
                    "id": str(team.id),
                    "name": team.name,
                    "type": "empaque" if PackagingTeams.EMPAQUE1.value.lower() in team.name.lower() else
                           "empaque2" if PackagingTeams.EMPAQUE2.value.lower() in team.name.lower() else
                           "empaque3" if PackagingTeams.EMPAQUE3.value.lower() in team.name.lower() else
                           "empaque4" if PackagingTeams.EMPAQUE4.value.lower() in team.name.lower() else
                           "maquina1" if PackagingTeams.MAQUINA1.value.lower() in team.name.lower() else
                           "maquina2" if PackagingTeams.MAQUINA2.value.lower() in team.name.lower() else "otro"
                } for team in packaging_teams
            ],
            "teams_by_type": {
                "empaque": empaque_team,
                "empaque2": empaque2_team,
                "empaque3": empaque3_team,
                "empaque4": empaque4_team,
                "maquina1": maquina1_team,
                "maquina2": maquina2_team
            },
            "total_packaging_teams": len(packaging_teams)
        }
    
    @staticmethod
    def get_specific_packaging_team_for_activity(activity_name: str, activity_description: str, teams_data: Dict) -> Dict[str, Any]:
        """
        Determina el equipo específico para una actividad de empaque según las reglas de negocio.
        
        Reglas:
        1. Empaque: Actividades "EMPAQUE MANUAL GRUPO"
        2. Empaque 3: Actividades "EMPAQUE MANUAL"
        3. Empaque 2: Descripción que contenga "esencia"
        4. Empaque 4: Actividades "EMPAQUE MANUAL MAS MEZCLA"
        5. MAQUINA 1: Actividades "EMPAQUE MAQUINA SEMI AUTOMATICA"
        6. MAQUINA 2: Actividades "EMPAQUE MAQUINA AUTOMATICA"
        
        Args:
            activity_name: Nombre de la actividad
            activity_description: Descripción de la actividad
            teams_data: Datos de equipos obtenidos de get_packaging_teams
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        activity_upper = activity_name.upper() if activity_name else ""
        description_lower = activity_description.lower() if activity_description else ""
        
        teams_by_type = teams_data.get("teams_by_type", {})
        
        # Regla 1: Empaque para actividades "EMPAQUE MANUAL GRUPO"
        if PackagingActivities.Emp_grupo.value.upper() in activity_upper:
            empaque_team = teams_by_type.get("empaque")
            if empaque_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque_team.id),
                        "name": empaque_team.name,
                        "type": "empaque"
                    },
                    "reason": f"Actividad de empaque manual grupo: {activity_name}",
                    "rule_applied": "empaque_manual_grupo"
                }
        
        # Regla 2: Empaque 3 para actividades "EMPAQUE MANUAL"
        if PackagingActivities.Emp_manual.value.upper() in activity_upper:
            empaque3_team = teams_by_type.get("empaque3")
            if empaque3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque3_team.id),
                        "name": empaque3_team.name,
                        "type": "empaque3"
                    },
                    "reason": f"Actividad de empaque manual: {activity_name}",
                    "rule_applied": "empaque_manual"
                }
        
        # Regla 3: Empaque 2 para descripciones con "esencia"
        if "esencia" in description_lower:
            empaque2_team = teams_by_type.get("empaque2")
            if empaque2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque2_team.id),
                        "name": empaque2_team.name,
                        "type": "empaque2"
                    },
                    "reason": f"Descripción contiene 'esencia': {activity_description}",
                    "rule_applied": "esencia"
                }
        
        # Regla 4: Empaque 4 para actividades "EMPAQUE MANUAL MAS MEZCLA"
        if PackagingActivities.Emp_mezcla.value.upper() in activity_upper:
            empaque4_team = teams_by_type.get("empaque4")
            if empaque4_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque4_team.id),
                        "name": empaque4_team.name,
                        "type": "empaque4"
                    },
                    "reason": f"Actividad de empaque manual más mezcla: {activity_name}",
                    "rule_applied": "empaque_manual_mezcla"
                }
        
        # Regla 5: MAQUINA 1 para actividades "EMPAQUE MAQUINA SEMI AUTOMATICA"
        if PackagingActivities.Emp_semi.value.upper() in activity_upper:
            maquina1_team = teams_by_type.get("maquina1")
            if maquina1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(maquina1_team.id),
                        "name": maquina1_team.name,
                        "type": "maquina1"
                    },
                    "reason": f"Actividad de máquina semi-automática: {activity_name}",
                    "rule_applied": "maquina_semi_automatica"
                }
        
        # Regla 6: MAQUINA 2 para actividades "EMPAQUE MAQUINA AUTOMATICA"
        if PackagingActivities.Emp_auto.value.upper() in activity_upper:
            maquina2_team = teams_by_type.get("maquina2")
            if maquina2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(maquina2_team.id),
                        "name": maquina2_team.name,
                        "type": "maquina2"
                    },
                    "reason": f"Actividad de máquina automática: {activity_name}",
                    "rule_applied": "maquina_automatica"
                }
        
        # Si no se puede aplicar ninguna regla, usar el primer equipo disponible
        available_teams = [
            teams_by_type.get("empaque"), 
            teams_by_type.get("empaque3"), 
            teams_by_type.get("empaque2"), 
            teams_by_type.get("empaque4"),
            teams_by_type.get("maquina1"),
            teams_by_type.get("maquina2")
        ]
        
        for team in available_teams:
            if team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(team.id),
                        "name": team.name,
                        "type": "fallback"
                    },
                    "reason": f"Equipo de respaldo: {team.name}",
                    "rule_applied": "fallback"
                }
        
        return {
            "success": False,
            "selected_team": None,
            "reason": "No se encontró equipo disponible para la actividad",
            "rule_applied": "none"
        }
