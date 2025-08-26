"""
Script para migrar automáticamente los usos de servicios originales en routes_order.py
"""

import re
from typing import List, Tuple


def migrate_routes_order_file(file_path: str) -> Tuple[bool, List[str]]:
    """
    Migra automáticamente los usos de servicios originales en routes_order.py
    
    Args:
        file_path: Ruta al archivo routes_order.py
        
    Returns:
        Tupla con (éxito, lista de cambios realizados)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        changes = []
        original_content = content
        
        # 1. Reemplazar imports
        if 'from app.services.weighing_task_service import WeighingTaskService' in content:
            content = content.replace(
                'from app.services.weighing_task_service import WeighingTaskService',
                ''
            )
            changes.append("Eliminado import de WeighingTaskService")
        
        if 'from app.services.fabrication_task_service import FabricationTaskService' in content:
            content = content.replace(
                'from app.services.fabrication_task_service import FabricationTaskService',
                ''
            )
            changes.append("Eliminado import de FabricationTaskService")
        
        # Agregar import del factory si no existe
        if 'from app.services.factory import TaskServiceFactory' not in content:
            # Buscar la línea después de los imports de task_config
            task_config_import = 'from app.core.task_config import ('
            if task_config_import in content:
                # Insertar después del bloque de imports de task_config
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == ')' and i > 0 and 'task_config' in lines[i-1]:
                        lines.insert(i + 1, 'from app.services.factory import TaskServiceFactory')
                        break
                content = '\n'.join(lines)
                changes.append("Agregado import de TaskServiceFactory")
        
        # 2. Agregar función helper si no existe
        if 'def get_task_services():' not in content:
            # Buscar después de la definición del router
            router_pattern = r'router = APIRouter\(prefix="/orders", tags=\["orders"\]\)'
            match = re.search(router_pattern, content)
            if match:
                helper_function = '''
def get_task_services():
    """Obtiene instancias de los servicios de tareas usando el factory"""
    weighing_service = TaskServiceFactory.create_weighing_service()
    fabrication_service = TaskServiceFactory.create_fabrication_service()
    return weighing_service, fabrication_service'''
                
                content = content[:match.end()] + helper_function + content[match.end():]
                changes.append("Agregada función helper get_task_services()")
        
        # 3. Reemplazar usos de WeighingTaskService
        # Patrón para métodos estáticos
        static_methods = [
            'get_activities_for_orders',
            'filter_weighing_activities',
            'get_activity_details_by_code_and_activity',
            'calculate_minutes_from_performance_and_quantity',
            'get_weighing_activities_with_minutes',
            'get_most_suitable_weighing_team',
            'get_available_programmings_for_team',
            'verify_programming_time_limit',
            '_get_pesado_activity_for_order'
        ]
        
        for method in static_methods:
            old_pattern = f'WeighingTaskService.{method}'
            if old_pattern in content:
                # Reemplazar con el patrón usando la función helper
                new_pattern = f'weighing_service.{method}'
                
                # Primero agregar la línea para obtener el servicio si no existe
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if old_pattern in line and 'weighing_service, _ = get_task_services()' not in '\n'.join(lines[max(0, i-5):i]):
                        # Buscar el inicio del bloque de función
                        function_start = i
                        for j in range(i, max(0, i-20), -1):
                            if lines[j].strip().startswith('def ') or lines[j].strip().startswith('@router'):
                                function_start = j
                                break
                        
                        # Verificar si ya hay una línea para obtener el servicio en este bloque
                        block_lines = lines[function_start:i]
                        if 'weighing_service, _ = get_task_services()' not in '\n'.join(block_lines):
                            # Agregar la línea para obtener el servicio
                            indent = len(lines[i]) - len(lines[i].lstrip())
                            service_line = ' ' * indent + 'weighing_service, _ = get_task_services()'
                            lines.insert(i, service_line)
                            content = '\n'.join(lines)
                            changes.append(f"Agregada línea para obtener weighing_service antes de usar {method}")
                            break
                
                # Ahora reemplazar el uso del método
                content = content.replace(old_pattern, new_pattern)
                changes.append(f"Reemplazado WeighingTaskService.{method} con weighing_service.{method}")
        
        # 4. Reemplazar usos de FabricationTaskService
        fabrication_methods = [
            'get_activities_for_orders',
            'filter_fabrication_activities',
            'get_activity_details_by_code_and_activity',
            'calculate_minutes_from_performance_and_quantity',
            'get_fabrication_activities_with_minutes',
            'get_most_suitable_fabrication_team',
            'get_available_programmings_for_team',
            'verify_programming_time_limit',
            '_get_fabrication_activity_for_order',
            'create_fabrication_tasks_for_orders'
        ]
        
        for method in fabrication_methods:
            old_pattern = f'FabricationTaskService.{method}'
            if old_pattern in content:
                # Reemplazar con el patrón usando la función helper
                new_pattern = f'fabrication_service.{method}'
                
                # Primero agregar la línea para obtener el servicio si no existe
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if old_pattern in line and 'fabrication_service = get_task_services()' not in '\n'.join(lines[max(0, i-5):i]):
                        # Buscar el inicio del bloque de función
                        function_start = i
                        for j in range(i, max(0, i-20), -1):
                            if lines[j].strip().startswith('def ') or lines[j].strip().startswith('@router'):
                                function_start = j
                                break
                        
                        # Verificar si ya hay una línea para obtener el servicio en este bloque
                        block_lines = lines[function_start:i]
                        if 'fabrication_service = get_task_services()' not in '\n'.join(block_lines):
                            # Agregar la línea para obtener el servicio
                            indent = len(lines[i]) - len(lines[i].lstrip())
                            service_line = ' ' * indent + '_, fabrication_service = get_task_services()'
                            lines.insert(i, service_line)
                            content = '\n'.join(lines)
                            changes.append(f"Agregada línea para obtener fabrication_service antes de usar {method}")
                            break
                
                # Ahora reemplazar el uso del método
                content = content.replace(old_pattern, new_pattern)
                changes.append(f"Reemplazado FabricationTaskService.{method} con fabrication_service.{method}")
        
        # 5. Escribir el archivo actualizado
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        else:
            return True, ["No se encontraron cambios necesarios"]
            
    except Exception as e:
        return False, [f"Error durante la migración: {str(e)}"]


def main():
    """Función principal para ejecutar la migración"""
    file_path = "app/api/v1/routes_order.py"
    
    print("🔄 Iniciando migración automática de routes_order.py...")
    print("=" * 60)
    
    success, changes = migrate_routes_order_file(file_path)
    
    if success:
        print("✅ Migración completada exitosamente")
        print(f"📝 Cambios realizados: {len(changes)}")
        
        for i, change in enumerate(changes, 1):
            print(f"  {i}. {change}")
    else:
        print("❌ Error durante la migración")
        for change in changes:
            print(f"  - {change}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
