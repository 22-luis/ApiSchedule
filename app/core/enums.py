from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pendiente"
    IN_PROGRESS = "en_progreso"
    PAUSED = "pausada"
    COMPLETED = "completada"

class TaskType(str, Enum):
    M1 = "M1"
    M12 = "M12"
    M13 = "M13"
    M15 = "M15"
    # Add other task types if they exist

class WeighingTeams(str, Enum):
    PESADO1 = "Equipo de Pesado 1"
    PESADO2 = "Equipo de Pesado 2"

class WeighingActivities(str, Enum):
    PESADO = "PESADO"
    PESAR = "PESAR"
    PESO = "PESO"
    BALANZA = "BALANZA"
    WEIGHING = "WEIGHING"

class ManufacturingTeams(str, Enum):
    FABRICADO1 = "Fabricado 1"
    FABRICADO2 = "Fabricado 2"
    FABRICADO3 = "Fabricado 3"
    MOLINO = "Molino"

class ManufacturingActivities(str, Enum):
    MOL_PASTA = "Mol_pasta"
    MOL_POLVO = "Mol_polvo"
    MEZ_MAQUINA = "Mez_maquina"
    MEZ_POLVO = "Mez_polvo"
    MEZ_LIQUIDA = "mez_liquida"
    FABRICACION = "Fabricacion"

class PackagingTeams(str, Enum):
    EMPAQUE1 = "Empaque 1"
    EMPAQUE2 = "Empaque 2"
    EMPAQUE3 = "Empaque 3"
    EMPAQUE4 = "Empaque 4"
    MAQUINA1 = "Maquina 1"
    MAQUINA2 = "Maquina 2"

class PackagingActivities(str, Enum):
    EMP_GRUPO = "Emp_grupo"
    EMP_MANUAL = "Emp_manual"
    EMP_SEMI = "Emp_semi"
    EMP_AUTO = "Emp_auto"
    EMP_MEZCLA = "Emp_mezcla"
