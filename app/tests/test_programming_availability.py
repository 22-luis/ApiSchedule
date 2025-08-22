"""
Tests for programming availability functionality.
"""
import pytest
from datetime import datetime, time, date, timedelta
from sqlalchemy.orm import Session
from app.models.programming import Programming, ProgrammingTask
from app.models.task import Task
from app.models.team import Team
from app.models.state import ProgrammingStatus
from app.utils.programming_availability import (
    get_team_type,
    get_cutoff_time_for_team,
    check_programming_availability,
    update_programming_availability
)


class TestProgrammingAvailability:
    
    def test_get_team_type(self):
        """Test team type detection based on team name."""
        # Test pesado team
        pesado_team = Team(name="Pesado Principal")
        assert get_team_type(pesado_team) == "pesado"
        
        # Test fabricado team
        fabricado_team = Team(name="Fabricado 1")
        assert get_team_type(fabricado_team) == "fabricado"
        
        # Test molino team
        molino_team = Team(name="Molino 2")
        assert get_team_type(molino_team) == "molino"
        
        # Test other team
        other_team = Team(name="Otro Equipo")
        assert get_team_type(other_team) == "otro"
    
    def test_get_cutoff_time_for_team(self):
        """Test cutoff time determination based on team type."""
        # Test pesado team cutoff time
        pesado_team = Team(name="Pesado Principal")
        assert get_cutoff_time_for_team(pesado_team) == time(17, 40)
        
        # Test other team cutoff time
        other_team = Team(name="Fabricado 1")
        assert get_cutoff_time_for_team(other_team) == time(14, 40)
    
    def test_check_programming_availability_with_no_tasks(self, db: Session):
        """Test availability check when programming has no tasks."""
        team = Team(name="Test Team")
        db.add(team)
        db.commit()
        
        programming = Programming(
            date=date.today(),
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        db.add(programming)
        db.commit()
        
        # Should be available when no tasks
        assert check_programming_availability(db, programming) == True
    
    def test_check_programming_availability_with_early_task(self, db: Session):
        """Test availability check when last task ends before cutoff time."""
        team = Team(name="Test Team")
        db.add(team)
        db.commit()
        
        programming = Programming(
            date=date.today(),
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        db.add(programming)
        db.commit()
        
        # Create a task that ends at 14:00 (before 14:40 cutoff)
        task = Task(description="Test Task")
        db.add(task)
        db.commit()
        
        programming_task = ProgrammingTask(
            programming_id=programming.id,
            task_id=task.id,
            order=1,
            end_time=datetime.combine(date.today(), time(14, 0))
        )
        db.add(programming_task)
        db.commit()
        
        # Should be available when task ends before cutoff
        assert check_programming_availability(db, programming) == True
    
    def test_check_programming_availability_with_late_task(self, db: Session):
        """Test availability check when last task ends after cutoff time."""
        team = Team(name="Test Team")
        db.add(team)
        db.commit()
        
        programming = Programming(
            date=date.today(),
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        db.add(programming)
        db.commit()
        
        # Create a task that ends at 15:00 (after 14:40 cutoff + 5 min buffer)
        task = Task(description="Test Task")
        db.add(task)
        db.commit()
        
        programming_task = ProgrammingTask(
            programming_id=programming.id,
            task_id=task.id,
            order=1,
            end_time=datetime.combine(date.today(), time(15, 0))
        )
        db.add(programming_task)
        db.commit()
        
        # Should be unavailable when task ends after cutoff + buffer
        assert check_programming_availability(db, programming) == False
    
    def test_check_programming_availability_with_pesado_team(self, db: Session):
        """Test availability check with pesado team (17:40 cutoff)."""
        team = Team(name="Pesado Principal")
        db.add(team)
        db.commit()
        
        programming = Programming(
            date=date.today(),
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        db.add(programming)
        db.commit()
        
        # Create a task that ends at 18:00 (after 17:40 cutoff + 5 min buffer)
        task = Task(description="Test Task")
        db.add(task)
        db.commit()
        
        programming_task = ProgrammingTask(
            programming_id=programming.id,
            task_id=task.id,
            order=1,
            end_time=datetime.combine(date.today(), time(18, 0))
        )
        db.add(programming_task)
        db.commit()
        
        # Should be unavailable when task ends after pesado cutoff + buffer
        assert check_programming_availability(db, programming) == False
    
    def test_update_programming_availability(self, db: Session):
        """Test updating programming status based on availability check."""
        team = Team(name="Test Team")
        db.add(team)
        db.commit()
        
        programming = Programming(
            date=date.today(),
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        db.add(programming)
        db.commit()
        
        # Create a task that ends late
        task = Task(description="Test Task")
        db.add(task)
        db.commit()
        
        programming_task = ProgrammingTask(
            programming_id=programming.id,
            task_id=task.id,
            order=1,
            end_time=datetime.combine(date.today(), time(15, 0))
        )
        db.add(programming_task)
        db.commit()
        
        # Update availability - should change status to unavailable
        status_changed = update_programming_availability(db, programming)
        assert status_changed == True
        assert programming.status == ProgrammingStatus.unavailable
    
    def test_update_programming_availability_bidirectional(self, db: Session):
        """Test bidirectional status changes based on task end time."""
        team = Team(name="Test Team")
        db.add(team)
        db.commit()
        
        programming = Programming(
            date=date.today(),
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        db.add(programming)
        db.commit()
        
        # Create a task that ends late (15:00 - after cutoff)
        task = Task(description="Test Task")
        db.add(task)
        db.commit()
        
        programming_task = ProgrammingTask(
            programming_id=programming.id,
            task_id=task.id,
            order=1,
            end_time=datetime.combine(date.today(), time(15, 0))
        )
        db.add(programming_task)
        db.commit()
        
        # Should change to unavailable
        status_changed = update_programming_availability(db, programming)
        assert status_changed == True
        assert programming.status == ProgrammingStatus.unavailable
        
        # Now change the task end time to be early (14:00 - before cutoff)
        programming_task.end_time = datetime.combine(date.today(), time(14, 0))
        db.commit()
        
        # Should change back to available
        status_changed = update_programming_availability(db, programming)
        assert status_changed == True
        assert programming.status == ProgrammingStatus.available
    
    def test_update_programming_availability_pesado_bidirectional(self, db: Session):
        """Test bidirectional status changes for pesado team."""
        team = Team(name="Pesado Principal")
        db.add(team)
        db.commit()
        
        programming = Programming(
            date=date.today(),
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        db.add(programming)
        db.commit()
        
        # Create a task that ends late (18:00 - after pesado cutoff)
        task = Task(description="Test Task")
        db.add(task)
        db.commit()
        
        programming_task = ProgrammingTask(
            programming_id=programming.id,
            task_id=task.id,
            order=1,
            end_time=datetime.combine(date.today(), time(18, 0))
        )
        db.add(programming_task)
        db.commit()
        
        # Should change to unavailable
        status_changed = update_programming_availability(db, programming)
        assert status_changed == True
        assert programming.status == ProgrammingStatus.unavailable
        
        # Now change the task end time to be early (17:00 - before pesado cutoff)
        programming_task.end_time = datetime.combine(date.today(), time(17, 0))
        db.commit()
        
        # Should change back to available
        status_changed = update_programming_availability(db, programming)
        assert status_changed == True
        assert programming.status == ProgrammingStatus.available
    
    def test_update_programming_availability_edge_cases(self, db: Session):
        """Test edge cases around the cutoff times."""
        team = Team(name="Test Team")
        db.add(team)
        db.commit()
        
        programming = Programming(
            date=date.today(),
            team_id=team.id,
            status=ProgrammingStatus.available
        )
        db.add(programming)
        db.commit()
        
        # Test exactly at cutoff time (14:40) - should be available
        task1 = Task(description="Test Task 1")
        db.add(task1)
        db.commit()
        
        programming_task1 = ProgrammingTask(
            programming_id=programming.id,
            task_id=task1.id,
            order=1,
            end_time=datetime.combine(date.today(), time(14, 40))
        )
        db.add(programming_task1)
        db.commit()
        
        status_changed = update_programming_availability(db, programming)
        assert status_changed == False  # No change needed
        assert programming.status == ProgrammingStatus.available
        
        # Test at cutoff + 5 minutes (14:45) - should still be available
        programming_task1.end_time = datetime.combine(date.today(), time(14, 45))
        db.commit()
        
        status_changed = update_programming_availability(db, programming)
        assert status_changed == False  # No change needed
        assert programming.status == ProgrammingStatus.available
        
        # Test at cutoff + 6 minutes (14:46) - should be unavailable
        programming_task1.end_time = datetime.combine(date.today(), time(14, 46))
        db.commit()
        
        status_changed = update_programming_availability(db, programming)
        assert status_changed == True
        assert programming.status == ProgrammingStatus.unavailable
