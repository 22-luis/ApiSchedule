import os
import shutil
from pathlib import Path

def safe_move(src, dst):
    """Move file or directory from src to dst, creating dst parent if needed."""
    src_path = Path(src)
    dst_path = Path(dst)
    
    if not src_path.exists():
        print(f"Skipping: {src} does not exist")
        return

    if not dst_path.parent.exists():
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dst_path.parent}")

    try:
        shutil.move(str(src_path), str(dst_path))
        print(f"Moved: {src} -> {dst}")
    except Exception as e:
        print(f"Error moving {src} to {dst}: {e}")

def main():
    base_dir = Path("app")
    
    # Define the new structure mapping
    # Format: (source_path, destination_path)
    moves = [
        # Shared Core
        ("app/core/config.py", "app/shared/core/config.py"),
        ("app/core/config_simple.py", "app/shared/core/config_simple.py"),
        ("app/core/enums.py", "app/shared/core/enums.py"),
        
        # Shared DB
        ("app/db", "app/shared/db"),
        
        # Shared Utils
        ("app/utils", "app/shared/utils"),
        
        # Module: Core
        ("app/models/user.py", "app/modules/core/models/user.py"),
        ("app/models/team.py", "app/modules/core/models/team.py"),
        ("app/models/role.py", "app/modules/core/models/role.py"),
        ("app/schemas/user.py", "app/modules/core/schemas/user.py"),
        ("app/schemas/team.py", "app/modules/core/schemas/team.py"),
        ("app/api/v1/routes_auth.py", "app/modules/core/api/routes_auth.py"),
        ("app/api/v1/routes_user.py", "app/modules/core/api/routes_user.py"),
        ("app/api/v1/routes_team.py", "app/modules/core/api/routes_team.py"),
        
        # Module: Timer
        ("app/models/stopwatch.py", "app/modules/timer/models/stopwatch.py"),
        ("app/models/record_stopwatch.py", "app/modules/timer/models/record_stopwatch.py"),
        ("app/models/stopwatch_timer.py", "app/modules/timer/models/stopwatch_timer.py"),
        ("app/schemas/stopwatch.py", "app/modules/timer/schemas/stopwatch.py"),
        ("app/schemas/record_stopwatch.py", "app/modules/timer/schemas/record_stopwatch.py"),
        ("app/services/timer.py", "app/modules/timer/services/timer.py"),
        ("app/api/v1/routes_timer.py", "app/modules/timer/api/routes_timer.py"),
        ("app/api/v1/routes_record_stopwatch.py", "app/modules/timer/api/routes_record_stopwatch.py"),
        
        # Module: Programming
        ("app/models/programming.py", "app/modules/programming/models/programming.py"),
        ("app/models/task.py", "app/modules/programming/models/task.py"),
        ("app/models/order.py", "app/modules/programming/models/order.py"),
        ("app/models/code.py", "app/modules/programming/models/code.py"),
        ("app/models/preparation.py", "app/modules/programming/models/preparation.py"),
        ("app/models/task_status_log.py", "app/modules/programming/models/task_status_log.py"),
        ("app/models/state.py", "app/modules/programming/models/state.py"),
        ("app/schemas/programming.py", "app/modules/programming/schemas/programming.py"),
        ("app/schemas/task.py", "app/modules/programming/schemas/task.py"),
        ("app/schemas/order.py", "app/modules/programming/schemas/order.py"),
        ("app/schemas/code.py", "app/modules/programming/schemas/code.py"),
        ("app/schemas/preparation.py", "app/modules/programming/schemas/preparation.py"),
        ("app/schemas/task_status_log.py", "app/modules/programming/schemas/task_status_log.py"),
        ("app/services/base_task_service.py", "app/modules/programming/services/base_task_service.py"),
        ("app/services/fabrication_task_service.py", "app/modules/programming/services/fabrication_task_service.py"),
        ("app/services/packaging_task_service.py", "app/modules/programming/services/packaging_task_service.py"),
        ("app/services/weighing_task_service.py", "app/modules/programming/services/weighing_task_service.py"),
        ("app/services/factory.py", "app/modules/programming/services/factory.py"),
        ("app/services/config.py", "app/modules/programming/services/config.py"),
        ("app/core/task_config.py", "app/modules/programming/services/task_config.py"),
        ("app/api/v1/routes_programming.py", "app/modules/programming/api/routes_programming.py"),
        ("app/api/v1/routes_task.py", "app/modules/programming/api/routes_task.py"),
        ("app/api/v1/routes_order.py", "app/modules/programming/api/routes_order.py"),
        ("app/api/v1/routes_code.py", "app/modules/programming/api/routes_code.py"),
        ("app/api/v1/routes_preparation.py", "app/modules/programming/api/routes_preparation.py"),
        ("app/api/v1/routes_task_status_log.py", "app/modules/programming/api/routes_task_status_log.py"),
        ("app/api/v1/routes_calculations.py", "app/modules/programming/api/routes_calculations.py"),
        ("app/api/v1/routes_report.py", "app/modules/programming/api/routes_report.py"),
        
        # Module: Automation
        ("app/services/auto.py", "app/modules/automation/services/auto.py"),
        ("app/api/v1/routes_auto.py", "app/modules/automation/api/routes_auto.py"),
    ]

    print("Starting refactoring...")
    for src, dst in moves:
        safe_move(src, dst)
    
    # Cleanup empty directories
    dirs_to_check = ["app/api/v1", "app/api", "app/models", "app/schemas", "app/services", "app/core", "app/utils", "app/db"]
    for d in dirs_to_check:
        p = Path(d)
        if p.exists() and not any(p.iterdir()):
            p.rmdir()
            print(f"Removed empty directory: {d}")
        elif p.exists():
            print(f"Directory not empty, skipping removal: {d}")

    print("Refactoring complete.")

if __name__ == "__main__":
    main()
