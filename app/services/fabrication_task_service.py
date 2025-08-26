from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, time, date
import math

from app.models.team import Team
from app.models.programming import Programming, ProgrammingStatus
from app.models.programming import ProgrammingTask
from app.models.task import Task
from app.models.code import Code


class FabricationTaskService:
    """Servicio para manejar la creación de tareas de fabricación"""
    
    # Configuración de límites de tiempo - usar configuración de task_config.py
    from app.core.task_config import schedule_limits
    TIME_LIMIT = schedule_limits.default  # Usar límite por defecto para fabricación
    TOLERANCE_MINUTES = 5
    MAX_ALLOWED_MINUTES = TIME_LIMIT.hour * 60 + TIME_LIMIT.minute + TOLERANCE_MINUTES
    
    @staticmethod
    def get_time_limit_for_activity(activity_name: str) -> time:
        """
        Obtiene el límite de tiempo específico para una actividad de fabricación.
        Usa las configuraciones de task_config.py
        
        Args:
            activity_name: Nombre de la actividad
            
        Returns:
            Límite de tiempo para la actividad
        """
        from app.core.task_config import ManufacturingActivities, schedule_limits
        
        activity_upper = activity_name.upper()
        
        # Para actividades de molienda, usar límite por defecto
        if (ManufacturingActivities.Mol_pasta.value in activity_upper or 
            ManufacturingActivities.Mol_polvo.value in activity_upper):
            return schedule_limits.default
        
        # Para actividades de mezcla, usar límite por defecto
        if (ManufacturingActivities.Mez_polvo.value in activity_upper or 
            ManufacturingActivities.Mez_maquina.value in activity_upper or
            ManufacturingActivities.mez_liquida.value in activity_upper):
            return schedule_limits.default
        
        # Para actividades de fabricación, usar límite por defecto
        if ManufacturingActivities.Fabricacion.value in activity_upper:
            return schedule_limits.default
        
        # Por defecto, usar el límite por defecto
        return schedule_limits.default
    
    @staticmethod
    def get_specific_team_for_activity(activity_name: str, activity_description: str, teams_data: Dict) -> Dict[str, Any]:
        """
        Determina el equipo específico para una actividad según las reglas de negocio.
        
        Reglas:
        1. Molino: Actividades que contengan "MOLIENDA"
        2. Fabricado 2: Descripción que contenga "esencia" O actividad "MEZCLA LIQUIDA"
        3. Fabricado 1: Actividades "MEZCLA EN MAQUINA" o "MEZCLA MANUAL POLVO"
        4. Fabricado 3: Actividades "FABRICACION" con "ADEREZOS" o "JALEAS"
        
        Args:
            activity_name: Nombre de la actividad
            activity_description: Descripción de la actividad
            teams_data: Datos de equipos obtenidos de get_most_suitable_fabrication_team
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        from app.core.task_config import ManufacturingActivities
        
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
        if not hasattr(FabricationTaskService, '_distribution_counter'):
            FabricationTaskService._distribution_counter = 0
        
        FabricationTaskService._distribution_counter += 1
        
        if FabricationTaskService._distribution_counter % 2 == 1:
            # Impar: usar Fabricado 1
            if fabricado1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": f"Distribución automática: Fabricado 1 (tarea #{FabricationTaskService._distribution_counter})",
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
                    "reason": f"Distribución automática: Fabricado 3 (tarea #{FabricationTaskService._distribution_counter})",
                    "rule_applied": "distribucion_fabricado3"
                }
        
        # Si no se puede aplicar ninguna regla, usar el primer equipo disponible
        available_teams = [fabricado1_team, fabricado3_team, fabricado2_team, teams_by_type.get("molino")]
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
    def extract_order_data(orders: List) -> List[Dict[str, Any]]:
        """
        Extrae solo los campos lote, quantity y code de las órdenes.
        t
        Args:
            orders: Lista de objetos Order de la base de datos
            
        Returns:
            Lista de diccionarios con solo lote, quantity y code
        """
        extracted_data = []
        
        for order in orders:
            order_data = {
                "lote": order.lote,
                "quantity": order.quantity,
                "code": order.code
            }
            extracted_data.append(order_data)
        
        return extracted_data
    
    @staticmethod
    def get_activities_by_code(code: str, db: Session) -> Dict[str, Any]:
        """
        Obtiene todas las actividades para un código específico.
        
        Args:
            code: Código de la orden
            db: Sesión de base de datos
            
        Returns:
            Diccionario con las actividades del código
        """
        code_objs = db.query(Code).filter(Code.code == code).all()
        
        if not code_objs:
            return {
                "code": code,
                "activities": [],
                "total_activities": 0,
                "found": False
            }
        
        activities = []
        for code_obj in code_objs:
            activity_data = {
                "id": str(code_obj.id),
                "activity": getattr(code_obj, "activity", None),
                "description": getattr(code_obj, "description", None),
                "unit": getattr(code_obj, "unit", None),
                "type": getattr(code_obj, "type", None),
                "quantity": getattr(code_obj, "quantity", None),
                "time": getattr(code_obj, "time", None),
                "people": getattr(code_obj, "people", None),
                "performance": getattr(code_obj, "performance", None),
                "material": getattr(code_obj, "material", None),
                "presentation": getattr(code_obj, "presentation", None),
                "fabricationCode": getattr(code_obj, "fabricationCode", None),
                "usefulLife": getattr(code_obj, "usefulLife", None)
            }
            activities.append(activity_data)
        
        return {
            "code": code,
            "activities": activities,
            "total_activities": len(activities),
            "found": True
        }
    
    @staticmethod
    def get_activities_for_orders(extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades para todas las órdenes extraídas.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades organizadas por código
        """
        activities_by_code = {}
        unique_codes = set()
        
        for order in extracted_orders:
            code = order.get('code')
            if code:
                unique_codes.add(code)
        
        for code in unique_codes:
            activities_data = FabricationTaskService.get_activities_by_code(code, db)
            activities_by_code[code] = activities_data
        
        return {
            "activities_by_code": activities_by_code,
            "total_codes_processed": len(unique_codes),
            "codes_processed": list(unique_codes)
        }
    
    @staticmethod
    def filter_fabrication_activities(activities_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra las actividades para obtener solo las relacionadas con fabricación.
         Usa las configuraciones específicas de task_config.py
        
        Args:
            activities_data: Diccionario con todas las actividades organizadas por código
            
        Returns:
            Diccionario con solo las actividades de fabricación organizadas por código
        """
        from app.core.task_config import ManufacturingActivities
        
        fabrication_activities_by_code = {}
        
        activities_by_code = activities_data.get("activities_by_code", {})
        for code, code_data in activities_by_code.items():
            activities = code_data.get("activities", [])
            fabrication_activities = []
            
            for activity in activities:
                activity_name = activity.get("activity", "").upper()
                
                # Usar las actividades definidas en ManufacturingActivities
                manufacturing_activities = [
                    ManufacturingActivities.Mol_pasta.value,
                    ManufacturingActivities.Mol_polvo.value,
                    ManufacturingActivities.Mez_polvo.value,
                    ManufacturingActivities.Mez_maquina.value,
                    ManufacturingActivities.mez_liquida.value,
                    ManufacturingActivities.Fabricacion.value
                ]
                
                # Buscar actividades relacionadas con fabricación usando las configuraciones
                if any(manufacturing_activity in activity_name for manufacturing_activity in manufacturing_activities):
                    fabrication_activities.append(activity)
                else:
                    # También buscar palabras clave adicionales como respaldo
                    fabrication_keywords = [
                        "FABRICACION", "FABRICACIÓN", "FABRICAR", "PRODUCCION", 
                        "PRODUCCIÓN", "PRODUCIR", "MANUFACTURA", "MANUFACTURAR", "ELABORACION",
                        "ELABORACIÓN", "ELABORAR", "PROCESO", "PROCESAR", "TRANSFORMACION",
                        "TRANSFORMACIÓN", "TRANSFORMAR", "FABRICATION", "MANUFACTURING",
                        "PRODUCTION", "PROCESSING"
                    ]
                    
                    if any(keyword in activity_name for keyword in fabrication_keywords):
                        fabrication_activities.append(activity)
            
            if fabrication_activities:
                fabrication_activities_by_code[code] = {
                    "code": code,
                    "fabrication_activities": fabrication_activities,
                    "total_fabrication_activities": len(fabrication_activities),
                    "found": True
                }
        
        return {
            "fabrication_activities_by_code": fabrication_activities_by_code,
            "total_codes_with_fabrication": len(fabrication_activities_by_code),
            "codes_with_fabrication": list(fabrication_activities_by_code.keys())
        }
    
    @staticmethod
    def calculate_minutes_from_performance_and_quantity(performance: float, quantity: int, time: float = None) -> int:
        """
        Calcula los minutos multiplicando performance (en horas) con la cantidad de la orden.
        Si performance es None, usa el campo time como alternativa.
        
        Args:
            performance: Rendimiento de la actividad en horas
            quantity: Cantidad de la orden
            time: Tiempo base de la actividad en minutos (usado directamente si performance es None)
            
        Returns:
            Minutos calculados (entero con ceiling)
        """
        if quantity is None:
            return 0
        
        if performance is not None:
            # Usar performance si está disponible
            # Fórmula: performance (horas) * quantity * 60 = minutos
            hours = performance * quantity
            minutes = hours * 60
            return math.ceil(minutes)
        elif time is not None:
            # Usar time directamente como minutos cuando performance es None
            # No multiplicar por quantity, usar el valor de time tal como está
            minutes = time
            return math.ceil(minutes)
        else:
            # Si no hay performance ni time, usar un valor por defecto
            # 30 minutos como fallback
            minutes = 30
            return math.ceil(minutes)
    
    @staticmethod
    def get_activity_details_by_code_and_activity(code: str, activity: str, db: Session) -> Dict[str, Any]:
        """
        Obtiene los datos detallados de una actividad específica.
        
        Args:
            code: Código del producto
            activity: Nombre de la actividad
            db: Sesión de base de datos
            
        Returns:
            Diccionario con los datos detallados de la actividad
        """
        code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
        
        if not code_obj:
            return {
                "success": False,
                "code": code,
                "activity": activity,
                "activity_details": None,
                "message": f"No se encontró código '{code}' con actividad '{activity}'"
            }
        
        activity_details = {
            "id": str(code_obj.id),
            "code": code_obj.code,
            "activity": code_obj.activity,
            "specification": code_obj.description,
            "people": code_obj.people,
            "performance": code_obj.performance,
            "material": code_obj.material,
            "presentation": code_obj.presentation,
            "fabricationCode": code_obj.fabricationCode,
            "usefulLife": code_obj.usefulLife,
            "unit": code_obj.unit,
            "type": code_obj.type,
            "description": code_obj.description,
            "quantity": code_obj.quantity,
            "time": code_obj.time
        }
        
        return {
            "success": True,
            "code": code,
            "activity": activity,
            "activity_details": activity_details,
            "message": f"Datos obtenidos exitosamente para código '{code}' y actividad '{activity}'"
        }
    
    @staticmethod
    def get_fabrication_activities_with_minutes(extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Obtiene las actividades de fabricación para todas las órdenes extraídas y calcula los minutos.
        
        Args:
            extracted_orders: Lista de órdenes extraídas (con lote, quantity, code)
            db: Sesión de base de datos
            
        Returns:
            Diccionario con actividades de fabricación y minutos calculados
        """
        # Obtener todas las actividades
        all_activities = FabricationTaskService.get_activities_for_orders(extracted_orders, db)
        
        # Filtrar solo las de fabricación
        fabrication_activities = FabricationTaskService.filter_fabrication_activities(all_activities)
        
        # Calcular minutos para cada actividad de fabricación
        fabrication_activities_with_minutes = {}
        fabrication_activities_by_code = fabrication_activities.get("fabrication_activities_by_code", {})
        
        for code, code_data in fabrication_activities_by_code.items():
            fabrication_activities_list = code_data.get("fabrication_activities", [])
            activities_with_minutes = []
            
            for activity_data in fabrication_activities_list:
                activity_name = activity_data.get("activity")
                if activity_name:
                    # Buscar la cantidad de la orden correspondiente
                    order_quantity = None
                    for order in extracted_orders:
                        if order.get("code") == code:
                            order_quantity = order.get("quantity")
                            break
                    
                    if order_quantity is not None:
                        # Calcular minutos
                        performance = activity_data.get("performance")
                        time = activity_data.get("time")
                        calculated_minutes = FabricationTaskService.calculate_minutes_from_performance_and_quantity(
                            performance, order_quantity, time
                        )
                        
                        # Calcular fórmula para mostrar
                        if performance is not None:
                            hours_calculation = performance * order_quantity
                            formula = f"{performance} horas * {order_quantity} = {hours_calculation} horas * 60 = {calculated_minutes} minutos (con ceiling)"
                        elif time is not None:
                            formula = f"{time} minutos (usado directamente) = {calculated_minutes} minutos (con ceiling)"
                        else:
                            formula = f"30 minutos (default) = {calculated_minutes} minutos (con ceiling)"
                        
                        # Calcular hours_calculation para compatibilidad
                        if performance is not None:
                            hours_calculation = performance * order_quantity
                        elif time is not None:
                            hours_calculation = time / 60  # Convertir minutos a horas
                        else:
                            hours_calculation = 30 / 60  # Convertir minutos a horas
                        
                        activities_with_minutes.append({
                            "activity_data": activity_data,
                            "minutes_calculation": {
                                "performance": performance,
                                "time": time,
                                "quantity": order_quantity,
                                "hours_calculation": hours_calculation,
                                "calculated_minutes": calculated_minutes,
                                "formula": formula
                            }
                        })
            
            if activities_with_minutes:
                fabrication_activities_with_minutes[code] = {
                    "code": code,
                    "fabrication_activities_with_minutes": activities_with_minutes,
                    "total_fabrication_activities": len(activities_with_minutes),
                    "found": True
                }
        
        return {
            "all_activities": all_activities,
            "fabrication_activities": fabrication_activities,
            "fabrication_activities_with_minutes": {
                "fabrication_activities_with_minutes_by_code": fabrication_activities_with_minutes,
                "total_codes_with_fabrication_minutes": len(fabrication_activities_with_minutes),
                "codes_with_fabrication_minutes": list(fabrication_activities_with_minutes.keys())
            },
            "total_orders_processed": len(extracted_orders)
        }
    
    @staticmethod
    def get_most_suitable_fabrication_team(db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de fabricación disponibles.
        Usa las configuraciones específicas de task_config.py
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información de todos los equipos de fabricación
        """
        from app.core.task_config import ManufacturingTeams
        
        # Usar los equipos definidos en ManufacturingTeams
        manufacturing_team_names = [
            ManufacturingTeams.Fabricado1.value,
            ManufacturingTeams.Fabricado2.value,
            ManufacturingTeams.Fabricado3.value,
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
            elif ManufacturingTeams.Fabricado1.value.lower() in team_name_lower:
                fabricado1_teams.append(team)
            elif ManufacturingTeams.Fabricado2.value.lower() in team_name_lower:
                fabricado2_teams.append(team)
            elif ManufacturingTeams.Fabricado3.value.lower() in team_name_lower:
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
                           "fabricado1" if ManufacturingTeams.Fabricado1.value.lower() in team.name.lower() else
                           "fabricado2" if ManufacturingTeams.Fabricado2.value.lower() in team.name.lower() else
                           "fabricado3" if ManufacturingTeams.Fabricado3.value.lower() in team.name.lower() else "otro"
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
    def get_available_programmings_for_team(team_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Obtiene las programaciones disponibles para un equipo específico.
        Devuelve todas las programaciones futuras ordenadas por fecha (más cercana primero).
        
        Args:
            team_id: ID del equipo
            db: Sesión de base de datos
            
        Returns:
            Lista de programaciones disponibles ordenadas por fecha
        """
        current_date = date.today()
        
        # Buscar programaciones disponibles ordenadas por fecha (más cercana primero)
        available_programmings = (
            db.query(Programming)
            .filter(
                Programming.team_id == team_id,
                Programming.date >= current_date,
                Programming.status == ProgrammingStatus.available
            )
            .order_by(Programming.date)
            .all()
        )
        
        # Si no hay programaciones disponibles, crear una nueva
        if not available_programmings:
            new_programmings = FabricationTaskService._create_new_programming(team_id, db)
            if new_programmings:
                available_programmings = new_programmings
        
        # Preparar datos de programaciones con información adicional
        programming_data = []
        for programming in available_programmings:
            # Calcular días hasta la programación
            days_until = (programming.date - current_date).days
            is_current_month = programming.date.month == current_date.month and programming.date.year == current_date.year
            
            programming_info = {
                "id": str(programming.id),
                "date": programming.date.isoformat(),
                "status": programming.status.value if programming.status else "available",
                "team_id": str(programming.team_id),
                "total_tasks": len(programming.programming_tasks) if programming.programming_tasks else 0,
                "is_newly_created": programming in new_programmings if 'new_programmings' in locals() else False,
                "days_until": days_until,
                "is_current_month": is_current_month,
                "priority": "high" if is_current_month and days_until <= 7 else "normal"
            }
            programming_data.append(programming_info)
        
        return programming_data
    
    @staticmethod
    def _create_new_programming(team_id: str, db: Session) -> List[Programming]:
        """
        Crea una nueva programación para el equipo usando fechas más cercanas.
        Busca huecos en las programaciones existentes.
        
        Args:
            team_id: ID del equipo
            db: Sesión de base de datos
            
        Returns:
            Lista con la nueva programación creada
        """
        current_date = date.today()
        
        # Buscar programaciones existentes del equipo ordenadas por fecha
        existing_programmings = (
            db.query(Programming)
            .filter(Programming.team_id == team_id)
            .order_by(Programming.date)
            .all()
        )
        
        # Buscar el primer hueco disponible en las próximas 30 días
        start_date = current_date + timedelta(days=1)  # Empezar desde mañana
        end_date = current_date + timedelta(days=30)   # Buscar hasta 30 días
        
        # Crear lista de fechas disponibles
        available_dates = []
        current_check_date = start_date
        
        while current_check_date <= end_date:
            # Evitar domingos
            if current_check_date.weekday() != 6:
                # Verificar si ya existe una programación para esta fecha
                existing_programming = (
                    db.query(Programming)
                    .filter(Programming.team_id == team_id, Programming.date == current_check_date)
                    .first()
                )
                
                if not existing_programming:
                    available_dates.append(current_check_date)
            
            current_check_date += timedelta(days=1)
        
        # Si no hay fechas disponibles en los próximos 30 días, usar la lógica anterior
        if not available_dates:
            if existing_programmings:
                # Usar la fecha siguiente a la última programación
                last_programming = existing_programmings[-1]
                new_date = last_programming.date + timedelta(days=1)
            else:
                # Si no hay programaciones, empezar desde mañana
                new_date = current_date + timedelta(days=1)
            
            # Evitar domingos
            while new_date.weekday() == 6:
                new_date += timedelta(days=1)
            
            # Verificar que no exista ya una programación para esa fecha
            existing_programming = (
                db.query(Programming)
                .filter(Programming.team_id == team_id, Programming.date == new_date)
                .first()
            )
            
            if existing_programming:
                # Buscar la siguiente fecha disponible
                while existing_programming:
                    new_date += timedelta(days=1)
                    while new_date.weekday() == 6:
                        new_date += timedelta(days=1)
                    existing_programming = (
                        db.query(Programming)
                        .filter(Programming.team_id == team_id, Programming.date == new_date)
                        .first()
                    )
        else:
            # Usar la primera fecha disponible
            new_date = available_dates[0]
        
        # Crear la nueva programación
        new_programming = Programming(
            team_id=team_id,
            date=new_date,
            status=ProgrammingStatus.available
        )
        
        try:
            db.add(new_programming)
            db.commit()
            db.refresh(new_programming)
            return [new_programming]
        except Exception as e:
            db.rollback()
            return []
    
    @staticmethod
    def verify_programming_time_limit(programmings: List[Dict], task_minutes: int, db: Session, 
                                    order_data: Optional[Dict] = None, 
                                    activity_details: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Verifica que al agregar una tarea a una programación no se exceda el límite de tiempo.
        Evalúa programaciones secuencialmente desde la más cercana hasta la más lejana.
        
        Args:
            programmings: Lista de programaciones disponibles ordenadas por fecha
            task_minutes: Minutos de la tarea a agregar
            db: Sesión de base de datos
            order_data: Datos de la orden (opcional)
            activity_details: Detalles de la actividad (opcional)
            
        Returns:
            Resultado de la verificación con programación seleccionada
        """
        current_date = date.today()
        
        # Asegurar que las programaciones estén ordenadas por fecha (más cercana primero)
        sorted_programmings = sorted(
            programmings,
            key=lambda p: (
                datetime.strptime(p.get("date", "9999-12-31"), "%Y-%m-%d").date() - current_date
            ).days
        )
        
        # Evaluar cada programación secuencialmente
        for programming in sorted_programmings:
            programming_id = programming.get("id")
            programming_date = programming.get("date")
            
            # Verificar que la programación esté en fecha actual o futura
            try:
                programming_date_obj = datetime.strptime(programming_date, "%Y-%m-%d").date()
                if programming_date_obj < current_date:
                    continue
            except:
                continue
            
            # Obtener la programación completa de la base de datos
            programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
            if not programming_obj:
                continue
            
            # Verificar que la programación esté disponible
            if programming_obj.status != ProgrammingStatus.available:
                continue
            
            # Obtener las tareas de la programación
            programming_tasks = db.query(ProgrammingTask).filter(
                ProgrammingTask.programming_id == programming_id
            ).all()
            
            # Calcular el tiempo actual de la programación
            current_end_minutes = FabricationTaskService._calculate_current_programming_time(
                programming_tasks, programming_date_obj
            )
            
            # Calcular el tiempo final si se agrega la nueva tarea
            final_minutes = current_end_minutes + task_minutes
            
            # Obtener el límite de tiempo específico para la actividad si se proporcionan los datos
            activity_time_limit = FabricationTaskService.TIME_LIMIT
            if order_data and activity_details:
                activity_name = activity_details.get('activity', '')
                if activity_name:
                    activity_time_limit = FabricationTaskService.get_time_limit_for_activity(activity_name)
            
            # Calcular el límite máximo en minutos para esta actividad
            activity_max_minutes = activity_time_limit.hour * 60 + activity_time_limit.minute + FabricationTaskService.TOLERANCE_MINUTES
            
            # Verificar si se excede el límite de tiempo
            if final_minutes <= activity_max_minutes:
                # Obtener información del equipo
                team_obj = db.query(Team).filter(Team.id == programming_obj.team_id).first()
                team_name = team_obj.name if team_obj else "Equipo desconocido"
                
                result = {
                    "success": True,
                    "message": f"Programación seleccionada: {programming_date} - Cumple con límite de tiempo",
                    "selected_programming": {
                        "id": programming_id,
                        "date": programming_date,
                        "team_id": str(programming_obj.team_id),
                        "team_name": team_name,
                        "task_minutes": task_minutes,
                        "time_limit": activity_time_limit.isoformat(),
                        "tolerance_minutes": FabricationTaskService.TOLERANCE_MINUTES,
                        "current_tasks": len(programming_tasks),
                        "current_end_minutes": current_end_minutes,
                        "final_minutes": final_minutes,
                        "activity_specific_limit": True
                    },
                    "verification_details": {
                        "current_end_minutes": current_end_minutes,
                        "final_minutes": final_minutes,
                        "max_allowed_minutes": activity_max_minutes,
                        "activity_time_limit": activity_time_limit.isoformat(),
                        "within_limit": True,
                        "programming_date": programming_date,
                        "total_existing_tasks": len(programming_tasks)
                    }
                }
                
                # Crear la tarea de la orden si se proporcionaron los datos
                if order_data and activity_details:
                    task_result = FabricationTaskService._create_order_task(
                        programming_id, programming_tasks, task_minutes,
                        order_data, activity_details, db
                    )
                    if task_result.get("success"):
                        result["order_task_created"] = task_result.get("task_data")
                
                return result
            else:
                # Si se excede el límite, continuar con la siguiente programación
                continue
        
        # Si ninguna programación cumple con el límite
        return {
            "success": False,
            "message": "Ninguna programación disponible cumple con el límite de tiempo",
            "selected_programming": None,
            "evaluated_programmings": len(sorted_programmings)
        }
    
    @staticmethod
    def _calculate_current_programming_time(programming_tasks: List[ProgrammingTask], 
                                          programming_date_obj: date) -> int:
        """
        Calcula el tiempo actual de una programación sumando los minutos de todas las tareas.
        
        Args:
            programming_tasks: Lista de tareas de la programación
            programming_date_obj: Fecha de la programación
            
        Returns:
            Minutos totales de todas las tareas de la programación
        """
        if not programming_tasks:
            # Programación vacía - usar 7:00 AM como tiempo base
            return 7 * 60
        
        # Sumar los minutos de todas las tareas
        total_minutes = 0
        valid_tasks = []
        
        for programming_task in programming_tasks:
            # Obtener la tarea asociada para acceder a los minutos
            task_minutes = None
            if hasattr(programming_task, 'task') and programming_task.task:
                task_minutes = programming_task.task.minutes
            
            if task_minutes is not None and task_minutes > 0:
                total_minutes += task_minutes
                valid_tasks.append(programming_task)
        
        if valid_tasks:
            return total_minutes
        else:
            # Si no hay tareas con minutos válidos, usar 7:00 AM
            return 7 * 60
    
    @staticmethod
    def _create_order_task(programming_id: str, programming_tasks: List[ProgrammingTask], 
                          task_minutes: int, order_data: Dict, activity_details: Dict, 
                          db: Session) -> Dict[str, Any]:
        """
        Crea la tarea de la orden en la programación.
        
        Args:
            programming_id: ID de la programación
            programming_tasks: Lista de tareas existentes
            task_minutes: Minutos de la tarea
            order_data: Datos de la orden
            activity_details: Detalles de la actividad
            db: Sesión de base de datos
            
        Returns:
            Resultado de la creación de la tarea
        """
        try:
            # Obtener la fecha de la programación
            programming_obj = db.query(Programming).filter(Programming.id == programming_id).first()
            programming_date = programming_obj.date if programming_obj else date.today()
            
            # Calcular start_time y end_time para la nueva tarea
            current_end_minutes = FabricationTaskService._calculate_current_programming_time(
                programming_tasks, programming_date
            )
            
            # Crear datetime para start_time usando la fecha de la programación
            task_start_time = datetime.combine(
                programming_date,
                time(hour=current_end_minutes // 60, minute=current_end_minutes % 60)
            )
            
            # Calcular end_time sumando los minutos
            task_end_time = task_start_time + timedelta(minutes=task_minutes)
            
            # Obtener el UUID del código específico para la actividad
            code_obj = db.query(Code).filter(
                Code.code == order_data.get('code'),
                Code.activity == activity_details.get('activity')
            ).first()
            code_id = code_obj.id if code_obj else None
            
            # Crear la tarea de la orden
            order_task_obj = Task(
                code_id=code_id,
                lote=str(order_data.get('lote')),
                quantity=order_data.get('quantity'),
                specification=activity_details.get('specification'),
                people=activity_details.get('people'),
                performance=activity_details.get('performance'),
                material=activity_details.get('material'),
                presentation=activity_details.get('presentation'),
                fabricationCode=activity_details.get('fabricationCode'),
                usefulLife=activity_details.get('usefulLife'),
                unit=activity_details.get('unit'),
                type=activity_details.get('type'),
                activity=activity_details.get('activity'),
                description=activity_details.get('description'),
                minutes=task_minutes,
                start_time=task_start_time,
                end_time=task_end_time
            )
            
            # Obtener el número de orden para la nueva tarea
            new_task_order = len(programming_tasks) + 1
            
            # Crear la asociación con la programación
            order_programming_task = ProgrammingTask(
                programming_id=programming_id,
                task_id=order_task_obj.id,
                order=new_task_order,
                start_time=task_start_time,
                end_time=task_end_time
            )
            
            # Agregar la tarea a la base de datos
            db.add(order_task_obj)
            db.flush()
            order_programming_task.task_id = order_task_obj.id
            db.add(order_programming_task)
            db.commit()
            db.refresh(order_task_obj)
            db.refresh(order_programming_task)
            
            return {
                "success": True,
                "task_data": {
                    "task_id": str(order_task_obj.id),
                    "programming_id": str(order_programming_task.programming_id),
                    "order": new_task_order,
                    "start_time": task_start_time.isoformat(),
                    "end_time": task_end_time.isoformat(),
                    "minutes": task_minutes,
                    "description": order_task_obj.description,
                    "lote": order_task_obj.lote,
                    "quantity": order_task_obj.quantity
                }
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def create_fabrication_tasks_for_orders(extracted_orders: List[Dict], db: Session) -> Dict[str, Any]:
        """
        Función principal que maneja todo el proceso de creación de tareas de fabricación.
        
        Args:
            extracted_orders: Lista de órdenes extraídas con lote, quantity y code
            db: Sesión de base de datos
        
        Returns:
            Resultado del proceso con información de las tareas creadas
        """
        try:
            # Obtener actividades de fabricación con minutos calculados
            fabrication_activities_data = FabricationTaskService.get_fabrication_activities_with_minutes(
                extracted_orders, db
            )
            
            # Obtener todos los equipos de fabricación disponibles
            teams_result = FabricationTaskService.get_most_suitable_fabrication_team(db)
            
            if not teams_result.get("success"):
                return {
                    "success": False,
                    "message": "No se pudieron obtener equipos de fabricación",
                    "tasks_created": 0,
                    "total_orders": len(extracted_orders)
                }
            
            # Obtener programaciones disponibles para todos los equipos
            all_available_programmings = {}
            teams_by_type = teams_result.get("teams_by_type", {})
            
            for team_type, team in teams_by_type.items():
                if team:
                    team_programmings = FabricationTaskService.get_available_programmings_for_team(str(team.id), db)
                    all_available_programmings[team_type] = {
                        "team": team,
                        "programmings": team_programmings
                    }
            
            # Verificar que al menos un equipo tenga programaciones disponibles
            total_available_programmings = sum(
                len(data.get("programmings", [])) for data in all_available_programmings.values()
            )
            
            if total_available_programmings == 0:
                return {
                    "success": False,
                    "message": "No se encontraron programaciones disponibles para ningún equipo de fabricación",
                    "tasks_created": 0,
                    "total_orders": len(extracted_orders)
                }
            
            # Procesar cada orden
            created_tasks = []
            failed_orders = []
            
            for order_data in extracted_orders:
                # Obtener la actividad de fabricación específica para esta orden
                fabrication_activity = FabricationTaskService._get_fabrication_activity_for_order(
                    order_data, fabrication_activities_data
                )
                
                if not fabrication_activity:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "No se encontró actividad de fabricación válida"
                    })
                    continue
                
                task_minutes = fabrication_activity.get("minutes_calculation", {}).get("calculated_minutes", 0)
                activity_details = fabrication_activity.get("activity_data", {})
                
                if task_minutes <= 0:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": "Los minutos calculados no son válidos"
                    })
                    continue
                
                # Determinar el equipo específico para esta actividad
                activity_name = activity_details.get("activity", "")
                activity_description = activity_details.get("description", "")
                
                team_selection = FabricationTaskService.get_specific_team_for_activity(
                    activity_name, activity_description, teams_result
                )
                
                if not team_selection.get("success"):
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": f"No se pudo asignar equipo: {team_selection.get('reason')}"
                    })
                    continue
                
                selected_team = team_selection.get("selected_team")
                team_type = selected_team.get("type")
                
                # Obtener las programaciones del equipo seleccionado
                team_programmings_data = all_available_programmings.get(team_type)
                if not team_programmings_data:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": f"No se encontraron programaciones para el equipo {team_type}"
                    })
                    continue
                
                team_programmings = team_programmings_data.get("programmings", [])
                
                # Verificar límite de tiempo y crear tarea
                time_verification = FabricationTaskService.verify_programming_time_limit(
                    team_programmings, task_minutes, db, order_data, activity_details
                )
                
                if time_verification.get("success") and time_verification.get("order_task_created"):
                    created_tasks.append({
                        "order_data": order_data,
                        "selected_programming": time_verification.get("selected_programming"),
                        "order_task": time_verification.get("order_task_created"),
                        "team_assignment": {
                            "team_id": selected_team.get("id"),
                            "team_name": selected_team.get("name"),
                            "team_type": team_type,
                            "assignment_reason": team_selection.get("reason"),
                            "rule_applied": team_selection.get("rule_applied")
                        }
                    })
                else:
                    failed_orders.append({
                        "order_data": order_data,
                        "reason": time_verification.get("message", "Error desconocido"),
                        "team_assignment": {
                            "team_id": selected_team.get("id"),
                            "team_name": selected_team.get("name"),
                            "team_type": team_type,
                            "assignment_reason": team_selection.get("reason")
                        }
                    })
            
            return {
                "success": True,
                "message": f"Procesamiento completado. {len(created_tasks)} tareas creadas de {len(extracted_orders)} órdenes",
                "tasks_created": len(created_tasks),
                "total_orders": len(extracted_orders),
                "created_tasks": created_tasks,
                "failed_orders": failed_orders,
                "teams_data": teams_result.get("teams_by_type"),
                "fabrication_activities_data": fabrication_activities_data,
                "team_assignments_summary": {
                    "molino": len([task for task in created_tasks if task.get("team_assignment", {}).get("team_type") == "molino"]),
                    "fabricado1": len([task for task in created_tasks if task.get("team_assignment", {}).get("team_type") == "fabricado1"]),
                    "fabricado2": len([task for task in created_tasks if task.get("team_assignment", {}).get("team_type") == "fabricado2"]),
                    "fabricado3": len([task for task in created_tasks if task.get("team_assignment", {}).get("team_type") == "fabricado3"])
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error durante la creación de tareas de fabricación: {str(e)}",
                "tasks_created": 0,
                "total_orders": len(extracted_orders)
            }
    
    @staticmethod
    def _get_fabrication_activity_for_order(order_data: Dict, fabrication_activities_data: Dict) -> Optional[Dict]:
        """
        Obtiene la actividad de fabricación específica para una orden.
        Usa las configuraciones específicas de task_config.py
        
        Args:
            order_data: Datos de la orden (lote, quantity, code)
            fabrication_activities_data: Datos de actividades de fabricación con minutos calculados
            
        Returns:
            Actividad de fabricación específica para la orden o None si no se encuentra
        """
        from app.core.task_config import ManufacturingActivities
        
        order_code = order_data.get('code')
        if not order_code:
            return None
        
        # Buscar las actividades para el código de esta orden
        code_data = fabrication_activities_data.get("fabrication_activities_with_minutes", {}).get(
            "fabrication_activities_with_minutes_by_code", {}
        ).get(order_code)
        
        if not code_data or not code_data.get("fabrication_activities_with_minutes"):
            return None
        
        # Prioridad de actividades según ManufacturingActivities
        priority_activities = [
            ManufacturingActivities.Fabricacion.value,  # Prioridad más alta
            ManufacturingActivities.Mez_maquina.value,
            ManufacturingActivities.Mez_polvo.value,
            ManufacturingActivities.mez_liquida.value,
            ManufacturingActivities.Mol_pasta.value,
            ManufacturingActivities.Mol_polvo.value
        ]
        
        # Buscar actividades en orden de prioridad
        fabrication_activity = None
        for priority_activity in priority_activities:
            for activity in code_data["fabrication_activities_with_minutes"]:
                activity_name = activity.get("activity_data", {}).get("activity", "")
                if activity_name and priority_activity.upper() in activity_name.upper():
                    fabrication_activity = activity
                    break
            if fabrication_activity:
                break
        
        # Si no se encuentra ninguna actividad prioritaria, buscar "FABRICACION" como respaldo
        if not fabrication_activity:
            for activity in code_data["fabrication_activities_with_minutes"]:
                activity_name = activity.get("activity_data", {}).get("activity", "")
                if activity_name and "FABRICACION" in activity_name.upper():
                    fabrication_activity = activity
                    break
        
        # Si no se encuentra ninguna actividad específica, usar la primera actividad disponible
        if not fabrication_activity:
            fabrication_activity = code_data["fabrication_activities_with_minutes"][0]
        
        return fabrication_activity
  