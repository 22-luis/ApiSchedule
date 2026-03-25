from datetime import date
from typing import List, Optional
from app.modules.reports.repositories.report_repository import ReportRepository

class ReportService:
    def __init__(self, report_repo: ReportRepository):
        self.report_repo = report_repo

    def get_productivity_report(self, start_date: date, end_date: date, team_id: Optional[str] = None):
        results = self.report_repo.get_productivity_data(start_date, end_date, team_id)
        
        return [{
            "date": row.date,
            "team_name": row.team_name,
            "total_tasks": row.total_tasks,
            "completed_tasks": row.completed_tasks,
            "completion_rate": round(row.completed_tasks / row.total_tasks * 100, 2) if row.total_tasks > 0 else 0,
            "scheduled_minutes": row.scheduled_minutes,
            "real_minutes": round(row.real_minutes, 2),
            "time_efficiency": round(row.scheduled_minutes / row.real_minutes * 100, 2) if row.real_minutes > 0 else 0,
            "scheduled_quantity": row.scheduled_quantity,
            "real_quantity": row.real_quantity,
            "quantity_efficiency": round(row.real_quantity / row.scheduled_quantity * 100, 2) if row.scheduled_quantity > 0 else 0
        } for row in results]

    def get_orders_status_report(self, start_date: date, end_date: date):
        results = self.report_repo.get_orders_status_data(start_date, end_date)
        
        return [{
            "status": row.status.value,
            "total_orders": row.total_orders,
            "total_quantity": row.total_quantity,
            "received_quantity": row.received_quantity,
            "completion_percentage": round(row.received_quantity / row.total_quantity * 100, 2) if row.total_quantity > 0 else 0,
            "avg_processing_days": round(row.avg_processing_days, 2) if row.avg_processing_days else 0,
            "delayed_orders": row.delayed_orders
        } for row in results]

    def get_task_performance_report(self):
        results = self.report_repo.get_task_performance_data()

        return [{
            "fecha": row.fecha,
            "codigo": row.code,
            "descripcion": row.description,
            "lote": row.lote,
            "tipo": row.type,
            "actividad": row.activity,
            "horas": round(float(row.horas), 4) if row.horas else None,
            "cantidad_real": float(row.real_quantity) if row.real_quantity else None,
            "minutes": round(float(row.minutes), 4) if row.minutes else None,
            "personas": row.people,
            "total_horas": round(float(row.total_horas), 4) if row.total_horas else None,
            "proporcion": round(float(row.proporcion), 4) if row.proporcion else None
        } for row in results]

    def get_task_performance_group_report(self, year: Optional[int] = None, month: Optional[int] = None):
        results = self.report_repo.get_task_performance_group_data(year, month)

        if year is not None and month is not None:
            return [{
                "year": year,
                "month": month,
                "code": row.code,
                "description": row.description,
                "type": row.type,
                "sum_hours": round(float(row.sum_hours), 4) if row.sum_hours else None,
                "sum_quantity": float(row.sum_quantity) if row.sum_quantity else None,
                "avg_time_per_product": round(float(row.avg_time_per_product), 4) if row.avg_time_per_product else None,
                "people": row.people,
                "final_metric": round(float(row.final_metric), 4) if row.final_metric else None
            } for row in results]
        else:
            return [{
                "code": row.code,
                "description": row.description,
                "type": row.type,
                "sum_hours": round(float(row.sum_hours), 4) if row.sum_hours else None,
                "sum_quantity": float(row.sum_quantity) if row.sum_quantity else None,
                "avg_time_per_product": round(float(row.avg_time_per_product), 4) if row.avg_time_per_product else None,
                "people": row.people,
                "final_metric": round(float(row.final_metric), 4) if row.final_metric else None
            } for row in results]

    def get_team_performance_report(self, start_date: date, end_date: date):
        results = self.report_repo.get_team_performance_data(start_date, end_date)

        return [{
            "team_name": row.name,
            "total_days": row.total_days,
            "total_tasks": row.total_tasks,
            "completed_tasks": row.completed_tasks,
            "completion_rate": round(row.completed_tasks / row.total_tasks * 100, 2) if row.total_tasks > 0 else 0,
            "scheduled_minutes": row.scheduled_minutes,
            "real_minutes": round(row.real_minutes, 2),
            "time_efficiency": round(row.scheduled_minutes / row.real_minutes * 100, 2) if row.real_minutes > 0 else 0,
            "avg_task_minutes": round(row.avg_task_minutes, 2) if row.avg_task_minutes else 0
        } for row in results]
