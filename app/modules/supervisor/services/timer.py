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
            existing.real_start_time = datetime.now()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Check for historical records to resume accumulated time and state
        historical_records = self.db.query(SupRecordStopwatch).filter(
            SupRecordStopwatch.task_id == task_id,
            SupRecordStopwatch.supervisor_id == supervisor_id
        ).order_by(SupRecordStopwatch.creation_date.desc()).all()
        
        initial_duration = sum(float(r.accumulated_duration or 0) for r in historical_records)
        
        # Inherit latest verification state
        last_record = historical_records[0] if historical_records else None
        
        now_local = datetime.now()
        sup_stopwatch = SupStopwatch(
            task_id=task_id,
            supervisor_id=supervisor_id,
            status=TimerStatus.RUNNING,
            accumulated_duration=initial_duration,
            real_start_time=now_local,
            created_at=now_local,
            # Inherited fields
            area_limpia=last_record.area_limpia if last_record else False,
            peso_verificado=last_record.peso_verificado if last_record else False,
            selladas=last_record.selladas if last_record else False,
            contenedores_limpios=last_record.contenedores_limpios if last_record else False,
            informacion_correcta=last_record.informacion_correcta if last_record else False,
            etiquetas_correctas=last_record.etiquetas_correctas if last_record else False,
            contenedores_correctos=last_record.contenedores_correctos if last_record else False,
            medidas_tomadas=last_record.medidas_tomadas if last_record else None
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

        now_local = datetime.now()
        last_start = (sup_stopwatch.real_start_time if sup_stopwatch.real_start_time else sup_stopwatch.created_at).replace(tzinfo=None)
        
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

        now_local = datetime.now()
        accumulated = float(sup_stopwatch.accumulated_duration or 0)

        if sup_stopwatch.status == TimerStatus.RUNNING:
            last_start = (sup_stopwatch.real_start_time if sup_stopwatch.real_start_time else sup_stopwatch.created_at).replace(tzinfo=None)
            elapsed = (now_local - last_start).total_seconds() / 3600
            accumulated += elapsed

        # Calcular el delta (solo el tiempo de esta sesión) para el registro histórico
        historical_records = self.db.query(SupRecordStopwatch).filter(
            SupRecordStopwatch.task_id == task_id,
            SupRecordStopwatch.supervisor_id == supervisor_id
        ).all()
        historical_sum = sum(float(r.accumulated_duration or 0) for r in historical_records)
        session_delta = accumulated - historical_sum

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

        record = SupRecordStopwatch(
            task_id=task_id,
            supervisor_id=supervisor_id,
            accumulated_duration=session_delta,
            comments=comments,
            medidas_tomadas=final_data["medidas_tomadas"],
            creation_date=now_local,
            real_start_time=sup_stopwatch.created_at.replace(tzinfo=None) if sup_stopwatch.created_at else None,
            real_end_time=now_local,
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
        # 1. Obtener temporizadores activos
        active_timers = self.db.query(SupStopwatch).filter(
            SupStopwatch.task_id.in_(task_ids),
            SupStopwatch.supervisor_id == supervisor_id
        ).all()
        
        active_task_ids = {timer.task_id for timer in active_timers}
        
        # 2. Para las tareas que NO tienen temporizador activo, buscar si tienen registros históricos
        remaining_task_ids = [tid for tid in task_ids if tid not in active_task_ids]
        historical_records = []
        if remaining_task_ids:
            historical_records = self.db.query(SupRecordStopwatch).filter(
                SupRecordStopwatch.task_id.in_(remaining_task_ids),
                SupRecordStopwatch.supervisor_id == supervisor_id
            ).order_by(SupRecordStopwatch.creation_date.asc()).all()

        results = []
        
        # Procesar activos
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
            
        # Procesar históricos (como 'stopped')
        # Agrupar por task_id porque puede haber múltiples sesiones
        hist_map = {}
        for rec in historical_records:
            tid = str(rec.task_id)
            if tid not in hist_map:
                hist_map[tid] = {
                    "task_id": tid,
                    "status": "stopped",
                    "accumulated_duration": 0.0,
                    "real_start_time": rec.real_start_time,
                    "area_limpia": rec.area_limpia,
                    "peso_verificado": rec.peso_verificado,
                    "selladas": rec.selladas,
                    "contenedores_limpios": rec.contenedores_limpios,
                    "informacion_correcta": rec.informacion_correcta,
                    "etiquetas_correctas": rec.etiquetas_correctas,
                    "contenedores_correctos": rec.contenedores_correctos,
                    "medidas_tomadas": rec.medidas_tomadas
                }
            hist_map[tid]["accumulated_duration"] += float(rec.accumulated_duration or 0)
            # Intentar mantener el check más reciente o alguna lógica de mezcla? 
            # Por ahora el último registro manda en los booleanos
            hist_map[tid].update({
                "area_limpia": rec.area_limpia,
                "peso_verificado": rec.peso_verificado,
                "selladas": rec.selladas,
                "contenedores_limpios": rec.contenedores_limpios,
                "informacion_correcta": rec.informacion_correcta,
                "etiquetas_correctas": rec.etiquetas_correctas,
                "contenedores_correctos": rec.contenedores_correctos,
                "medidas_tomadas": rec.medidas_tomadas
            })

        results.extend(hist_map.values())
        return results
