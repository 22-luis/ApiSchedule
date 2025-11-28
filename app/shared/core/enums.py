from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pendiente"
    IN_PROGRESS = "en_progreso"
    PAUSED = "pausada"
    COMPLETED = "completada"

class TaskType(str, Enum):
    M1 = "EMPAQUE MANUAL MAS MEZCLA"
    M2 = "EMPAQUE MANUAL GRUPO"
    M3 = "EMPAQUE BOLSA DE 50, 55 LB"
    M4 = "EMPAQUE MAQUINA SEMI AUTOMATICA"
    M5 = "EMPAQUE MAQUINA AUTOMATICA"
    M7 = "PESADO Y/O FABRICADO"
    M9 = "MOLIENDA POLVOS/HORNEO"
    M10 = "MOLIENDA EN PASTA"
    M11 = "MEZCLA MANUAL POLVO"
    M12 = "MEZCLA EN MAQUINA/EMPAQUE 25 KG"
    M13 = "MEZCLAS LIQUIDAS Y/O EMPAQUE"
    M15 = "FABRICACION DE ADEREZOS, JALEAS"

class WeighingTeams(str, Enum):
    PESADO = "Pesado "

class WeighingActivities(str, Enum):
    PESADO = "PESADO Y/O FABRICADO"

class ManufacturingTeams(str, Enum):
    FABRICADO1 = "Fabricado 1"
    FABRICADO2 = "Fabricado 2"
    FABRICADO3 = "Fabricado 3"
    MOLINO = "Molino"

class ManufacturingActivities(str, Enum):
    MOL_PASTA = "MOLIENDA EN PASTA"
    MOL_POLVO = "MOLIENDA POLVOS/HORNEO"
    MEZ_MAQUINA = "MEZCLA EN MAQUINA/EMPAQUE 25 KG"
    MEZ_POLVO = "MEZCLA MANUAL POLVO"
    MEZ_LIQUIDA = "MEZCLAS LIQUIDAS Y/O EMPAQUE"
    FABRICACION = "FABRICACION DE ADEREZOS, JALEAS"

class PackagingTeams(str, Enum):
    EMPAQUE1 = "Empaque 1"
    EMPAQUE2 = "Empaque 2"
    EMPAQUE3 = "Empaque 3"
    EMPAQUE4 = "Empaque 4"
    MAQUINA1 = "Maquina 1"
    MAQUINA2 = "Maquina 2"

class PackagingActivities(str, Enum):
    EMP_GRUPO = "EMPAQUE MANUAL GRUPO"
    EMP_MANUAL = "EMPAQUE BOLSA DE 50, 55 LB"
    EMP_SEMI = "EMPAQUE MAQUINA SEMI AUTOMATICA"
    EMP_AUTO = "EMPAQUE MAQUINA AUTOMATICA"
    EMP_MEZCLA = "EMPAQUE MANUAL MAS MEZCLA"
