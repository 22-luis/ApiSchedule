"""
Enums para la configuración de tareas y equipos.
Este archivo contiene todas las enumeraciones para evitar importaciones circulares.
"""

from enum import Enum

class WeighingTeams(str, Enum):
    Pesado = "Pesado"
    
class WeighingActivities(str, Enum):
    Pesado = "PESADO"
    
class ManufacturingTeams(str, Enum):
    Fabricado1 = "Fabricado 1"
    Fabricado2 = "Fabricado 2"
    Fabricado3 = "Fabricado 3"
    Molino = "Molino"
    
class ManufacturingActivities(str, Enum):
    Mol_pasta = "MOLIENDA EN PASTA"
    Mol_polvo = "MOLIENDA EN POLVO"
    Mez_polvo = "MEZCLA MANUAL POLVO"
    Mez_maquina = "MEZCLA EN MAQUINA"
    mez_liquida = "MEZCLA LIQUIDA"
    Fabricacion = "FABRICACION DE ADEREZOS, JALEAS"
    
class PackagingTeams(str, Enum):
    Empaque1 = "Empaque 1"
    Empaque2 = "Empaque 2"
    Empaque3 = "Empaque 3"
    Empaque4 = "Empaque 4"
    Maquina1 = "MAQUINA 1"
    Maquina2 = "MAQUINA 2"

class PackagingActivities(str, Enum):
    Emp_mezcla = " EMPAQUE MANUAL MAS MEZCLA"
    Emp_grupo = "EMPAQUE MANUAL GRUPO"
    Emp_manual = "EMPAQUE MANUAL"
    Emp_semi = "EMPAQUE MAQUINA SEMI AUTOMATICA"
    Emp_auto = "EMPAQUE MAQUINA AUTOMATICA"

class MandatoryTasks(str, Enum):
    """Tareas obligatorias que deben incluirse en todas las programaciones"""
    REUNION_PREPARACION = "REUNION Y PREPARACION DE AREA"
    ALMUERZO = "ALMUERZO"
    LIMPIEZA = "LIMPIEZA"
