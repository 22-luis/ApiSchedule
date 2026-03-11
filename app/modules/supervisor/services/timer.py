from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging

from app.modules.programming.models.task import Task
from app.modules.supervisor.models.sup_stopwatch import SupStopwatch
from app.modules.supervisor.models.sup_record_stopwatch import SupRecordStopwatch
from app.modules.timer.models.state import TimerStatus

logger = logging.getLogger(__name__)

class SupTimerService:
    def __init__(self, db: Session):
        self.db = db

    def start_supervision(self, task_id: uuid.UUID, supervisor_id: uuid.UUID):
        # Check if already supervising
        existing = self.db.query(SupStopwatch).filter(
            SupStopwatch.task_id == task_id,
            SupStopwatch.supervisor_id == supervisor_id
        ).first()
        
        if existing:
            if existing.status == TimerStatus.RUNNING:
                return existing
            # If paused, resume
            existing.status = TimerStatus.RUNNING
            existing.real_start_time = (datetime.now(timezone.utc) - timedelta(hours=6)).replace(tzinfo=None)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        now_local = (datetime.now(timezone.utc) - timedelta(hours=6)).replace(tzinfo=None)
        sup_stopwatch = SupStopwatch(
            task_id=task_id,
            supervisor_id=supervisor_id,
            status=TimerStatus.RUNNING,
            accumulated_duration=0,
            real_start_time=now_local,
            created_at=now_local
        )
        self.db.add(sup_stopwatch)
        self.db.commit()
        self.db.refresh(sup_stopwatch)
        return sup_stopwatch

    def pause_supervision(self, task_id: uuid.UUID, supervisor_id: uuid.UUID):
        sup_stopwatch = self.db.query(SupStopwatch).filter(
            SupStopwatch.task_id == task_id,
            SupStopwatch.supervisor_id == supervisor_id
        ).first()

        if not sup_stopwatch:
            raise ValueError(f"No supervision record found for task {task_id}")

        if sup_stopwatch.status == TimerStatus.PAUSED:
            return sup_stopwatch

        if sup_stopwatch.status != TimerStatus.RUNNING:
            return sup_stopwatch

        now_local = (datetime.now(timezone.utc) - timedelta(hours=6)).replace(tzinfo=None)
        last_start = sup_stopwatch.real_start_time.replace(tzinfo=None) if sup_stopwatch.real_start_time else sup_stopwatch.created_at.replace(tzinfo=None)
        
        elapsed = (now_local - last_start).total_seconds() / 3600
        
        sup_stopwatch.accumulated_duration = float(sup_stopwatch.accumulated_duration or 0) + elapsed
        sup_stopwatch.status = TimerStatus.PAUSED
        sup_stopwatch.real_end_time = now_local
        sup_stopwatch.updated_at = now_local
        
        self.db.commit()
        self.db.refresh(sup_stopwatch)
        return sup_stopwatch

    def update_supervision_data(self, task_id: uuid.UUID, supervisor_id: uuid.UUID, data: Dict[str, Any]):
        sup_stopwatch = self.db.query(SupStopwatch).filter(
            SupStopwatch.task_id == task_id,
            SupStopwatch.supervisor_id == supervisor_id
        ).first()

        if not sup_stopwatch:
            raise ValueError("No active supervision timer found to update")

        for key, value in data.items():
            if hasattr(sup_stopwatch, key) and value is not None:
                setattr(sup_stopwatch, key, value)
        
        self.db.commit()
        self.db.refresh(sup_stopwatch)
        return sup_stopwatch

    def stop_supervision(self, task_id: uuid.UUID, supervisor_id: uuid.UUID, comments: Optional[str] = None, verification_data: Optional[Dict[str, Any]] = None):
        sup_stopwatch = self.db.query(SupStopwatch).filter(
            SupStopwatch.task_id == task_id,
            SupStopwatch.supervisor_id == supervisor_id
        ).first()

        if not sup_stopwatch:
            raise ValueError("No supervision timer found")

        now_local = (datetime.now(timezone.utc) - timedelta(hours=6)).replace(tzinfo=None)
        accumulated = float(sup_stopwatch.accumulated_duration or 0)

        if sup_stopwatch.status == TimerStatus.RUNNING:
            last_start = sup_stopwatch.real_start_time.replace(tzinfo=None) if sup_stopwatch.real_start_time else sup_stopwatch.created_at.replace(tzinfo=None)
            elapsed = (now_local - last_start).total_seconds() / 3600
            accumulated += elapsed

        # Merge verification data
        final_data = {
            "area_limpia": sup_stopwatch.area_limpia,
            "peso_verificado": sup_stopwatch.peso_verificado,
            "selladas": sup_stopwatch.selladas,
            "contenedores_limpios": sup_stopwatch.contenedores_limpios,
            "informacion_correcta": sup_stopwatch.informacion_correcta,
            "etiquetas_correctas": sup_stopwatch.etiquetas_correctas,
            "contenedores_correctos": sup_stopwatch.contenedores_correctos,
            "medidas_tomadas": sup_stopwatch.medidas_tomadas
        }
        
        if verification_data:
            for k, v in verification_data.items():
                if v is not None:
                    final_data[k] = v

        # Create record
        record = SupRecordStopwatch(
            task_id=task_id,
            supervisor_id=supervisor_id,
            accumulated_duration=accumulated,
            comments=comments,
            medidas_tomadas=final_data["medidas_tomadas"],
            creation_date=now_local,
            area_limpia=final_data["area_limpia"],
            peso_verificado=final_data["peso_verificado"],
            selladas=final_data["selladas"],
            contenedores_limpios=final_data["contenedores_limpios"],
            informacion_correcta=final_data["informacion_correcta"],
            etiquetas_correctas=final_data["etiquetas_correctas"],
            contenedores_correctos=final_data["contenedores_correctos"]
        )
        self.db.add(record)
        
        # Delete active timer
        self.db.delete(sup_stopwatch)
        
        self.db.commit()
        return record

    def get_supervision_status(self, task_ids: List[uuid.UUID], supervisor_id: uuid.UUID):
        active_timers = self.db.query(SupStopwatch).filter(
            SupStopwatch.task_id.in_(task_ids),
            SupStopwatch.supervisor_id == supervisor_id
        ).all()
        
        results = []
        for timer in active_timers:
            results.append({
                "task_id": str(timer.task_id),
                "status": timer.status.value,
                "accumulated_duration": timer.accumulated_duration,
                "real_start_time": timer.real_start_time,
                "area_limpia": timer.area_limpia,
                "peso_verificado": timer.peso_verificado,
                "selladas": timer.selladas,
                "contenedores_limpios": timer.contenedores_limpios,
                "informacion_correcta": timer.informacion_correcta,
                "etiquetas_correctas": timer.etiquetas_correctas,
                "contenedores_correctos": timer.contenedores_correctos,
                "medidas_tomadas": timer.medidas_tomadas
            })
        return results
