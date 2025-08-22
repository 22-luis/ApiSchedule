"""
Utility functions for managing programming availability based on task end times and team types.
"""
from datetime import datetime, time, timedelta
from sqlalchemy.orm import Session
from app.models.programming import Programming, ProgrammingTask
from app.models.team import Team
from app.models.state import ProgrammingStatus
from typing import Optional


def get_team_type(team: Team) -> str:
    """
    Returns the team type based on the name (substring, not exact).
    Example: 'fabricado 1', 'molino 2', 'pesado principal'...
    """
    name = (team.name or '').lower()
    if "fabricado" in name:
        return "fabricado"
    if "molino" in name:
        return "molino"
    if "pesado" in name:
        return "pesado"
    return "otro"


def get_cutoff_time_for_team(team: Team) -> time:
    """
    Returns the cutoff time for a team based on its type.
    - Pesado teams: 17:40
    - Other teams: 14:40
    """
    team_type = get_team_type(team)
    if team_type == "pesado":
        return time(17, 40)  # 17:40 for pesado teams
    else:
        return time(14, 40)  # 14:40 for other teams


def check_programming_availability(db: Session, programming: Programming) -> bool:
    """
    Checks if a programming should be marked as unavailable based on the last task's end time.
    
    Returns True if the programming should be available, False if it should be unavailable.
    """
    # Get the last task in the programming
    last_programming_task = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.programming_id == programming.id)
        .order_by(ProgrammingTask.end_time.desc().nullslast())
        .first()
    )
    
    if not last_programming_task or not last_programming_task.end_time:
        return True  # No tasks or no end time, keep available
    
    # Get the team to determine cutoff time
    team = db.query(Team).filter(Team.id == programming.team_id).first()
    if not team:
        return True  # No team found, keep available
    
    cutoff_time = get_cutoff_time_for_team(team)
    max_extension = timedelta(minutes=5)  # Maximum 5 minutes extension
    
    # Create cutoff datetime for the programming date
    cutoff_datetime = datetime.combine(programming.date, cutoff_time)
    max_allowed_time = cutoff_datetime + max_extension
    
    # Check if the last task's end time exceeds the maximum allowed time
    if last_programming_task.end_time > max_allowed_time:
        return False  # Should be unavailable
    
    return True  # Should be available


def update_programming_availability(db: Session, programming: Programming) -> bool:
    """
    Updates the programming status based on the last task's end time.
    
    Bidirectional behavior:
    - If last task ends before/at cutoff time → Programming becomes "available"
    - If last task ends after cutoff time → Programming becomes "unavailable"
    
    Returns True if the status was changed, False if it remained the same.
    """
    should_be_available = check_programming_availability(db, programming)
    
    if should_be_available and programming.status == ProgrammingStatus.unavailable:
        programming.status = ProgrammingStatus.available
        db.commit()
        return True
    elif not should_be_available and programming.status == ProgrammingStatus.available:
        programming.status = ProgrammingStatus.unavailable
        db.commit()
        return True
    
    return False


def update_programming_availability_by_task(db: Session, task_id: str) -> None:
    """
    Updates the availability of all programmings that contain a specific task.
    This is useful when a task is created, updated, or deleted.
    """
    # Find all programmings that contain this task
    programming_tasks = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.task_id == task_id)
        .all()
    )
    
    for pt in programming_tasks:
        programming = db.query(Programming).filter(Programming.id == pt.programming_id).first()
        if programming:
            update_programming_availability(db, programming)


def update_all_programmings_availability_for_date(db: Session, target_date: datetime.date) -> dict:
    """
    Updates the availability of all programmings for a specific date.
    
    Returns a dictionary with the results of the operation.
    """
    programmings = db.query(Programming).filter(Programming.date == target_date).all()
    
    results = {
        "total_programmings": len(programmings),
        "status_changes": 0,
        "available_count": 0,
        "unavailable_count": 0
    }
    
    for programming in programmings:
        status_changed = update_programming_availability(db, programming)
        if status_changed:
            results["status_changes"] += 1
        
        if programming.status == ProgrammingStatus.available:
            results["available_count"] += 1
        else:
            results["unavailable_count"] += 1
    
    return results
