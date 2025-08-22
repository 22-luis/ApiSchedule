from typing import List, Dict, Any
from datetime import datetime, time, tinedelta
from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.team import Team
from app.models.programming import Programming
from app.core.task_config import ( 
                                  WeighingTeams,
                                  WeighingActivities,
                                  ManufacturingTeams, 
                                  ManufacturingActivities,
                                  PackagingTeams,
                                  PackagingActivities,
                                  ScheduleLimits)

class TaskAuto:
    
    def __init__(self, db: Session):
        self.db = db
        
    def weighing_tasks(
        self,
        progamming_id=str,
        team=WeighingTeams,
        activity=WeighingActivities,
        start_time=datetime,
        quantity=int,
        description=str,
        created_by_user_id=str
        ) -> Dict[str, Any]:
        
        try:
            if not self.validate_weighing_schedule(start_time):
                return {
                    "succes": False,
                    "error": "Schedule limit exceeded"
                }
                
            task = Task(
                programming_id=progamming_id,
                activity=activity.value,
                start_time=start_time,
                quantity=quantity,
                description=description,
                created_by_user_id=created_by_user_id
            )
            
            team = self._get_team_by_name(team.value)
            if team:
                task.teams = [team]
            self.db.add(task)
            self.db.commit()
            
            return {
                "success": True,
                "task_id": task.id
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
                
        
        