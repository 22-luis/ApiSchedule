from datetime import date
from typing import List, Optional
from sqlalchemy import func, case, and_, extract, select, cast, Float, distinct
from sqlalchemy.orm import Session
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task
from app.modules.organization.models.team import Team
from app.modules.orders.models.order import Order, OrderStatus
from app.modules.programming.models.state import ProgrammingStatus
from app.modules.codes.models.code import Code
from app.modules.timing.models.record_stopwatch import RecordStopwatch

class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_productivity_data(self, start_date: date, end_date: date, team_id: Optional[str] = None):
        real_minutes_subquery = (
            self.db.query(
                RecordStopwatch.task_id,
                func.sum(RecordStopwatch.accumulated_duration * 60).label('total_real_minutes')
            )
            .group_by(RecordStopwatch.task_id)
            .subquery()
        )

        query = (
            self.db.query(
                Programming.date,
                Team.name.label('team_name'),
                func.count(ProgrammingTask.task_id).label('total_tasks'),
                func.sum(case([(ProgrammingTask.is_completed == True, 1)], else_=0)).label('completed_tasks'),
                func.sum(Task.minutes).label('scheduled_minutes'),
                func.sum(func.coalesce(real_minutes_subquery.c.total_real_minutes, ProgrammingTask.duration_in_hours * 60, 0)).label('real_minutes'),
                func.sum(Task.quantity).label('scheduled_quantity'),
                func.sum(ProgrammingTask.real_quantity).label('real_quantity')
            )
            .join(Team, Programming.team_id == Team.id)
            .join(ProgrammingTask, Programming.id == ProgrammingTask.programming_id)
            .join(Task, ProgrammingTask.task_id == Task.id)
            .outerjoin(
                real_minutes_subquery,
                Task.id == real_minutes_subquery.c.task_id
            )
            .filter(
                Programming.date.between(start_date, end_date),
                Programming.status != ProgrammingStatus.cancelled
            )
            .group_by(Programming.date, Team.name)
            .order_by(Programming.date)
        )

        if team_id:
            query = query.filter(Team.id == team_id)

        return query.all()

    def get_orders_status_data(self, start_date: date, end_date: date):
        return (
            self.db.query(
                Order.status,
                func.count(Order.lote).label('total_orders'),
                func.sum(Order.quantity).label('total_quantity'),
                func.sum(Order.received_quantity).label('received_quantity'),
                func.avg(
                    case([
                        (Order.submitted_date != None,
                         func.extract('days', Order.submitted_date - Order.received_date))
                    ], else_=None)
                ).label('avg_processing_days'),
                func.count(
                    case([
                        (and_(
                            Order.status != OrderStatus.completed,
                            Order.dueDate < func.current_date()
                        ), Order.lote)
                    ])
                ).label('delayed_orders')
            )
            .filter(
                Order.received_date.between(start_date, end_date)
            )
            .group_by(Order.status)
            .all()
        )

    def get_task_performance_data(self):
        real_minutes_subquery = (
            self.db.query(
                RecordStopwatch.task_id,
                func.sum(RecordStopwatch.accumulated_duration * 60).label('total_real_minutes')
            )
            .group_by(RecordStopwatch.task_id)
            .subquery()
        )

        query = (
            select(
                func.date(ProgrammingTask.start_time).label('fecha'),
                Code.code,
                Code.description,
                Task.lote,
                Task.type,
                Task.activity,
               # (cast(1.0, Float) / func.nullif(Task.performance, 0)).label('horas'),#quitar esta columna
                #agregar columna productividad que sera cantidad/minutos  convertido a hora 
                (cast(ProgrammingTask.real_quantity, Float)/func.nullif(ProgrammingTask.duration_in_hours, 0)).label('productividad'),
                ProgrammingTask.real_quantity,
                func.coalesce(ProgrammingTask.duration_in_hours , 0).label('minutes'),#dejar en horas
                Task.people,
                (ProgrammingTask.duration_in_hours * Task.people).label('total_horas'),
                case(
                    (ProgrammingTask.real_quantity != 0,
                     ((1.0 / func.nullif(Task.performance, 0)) * Task.quantity) / cast(ProgrammingTask.real_quantity, Float)
                    ),
                    else_=None
                ).label('proporcion')
            )
            .select_from(Task)
            .join(Code, Task.code_id == Code.id)
            .join(ProgrammingTask, Task.id == ProgrammingTask.task_id)
            .outerjoin(
                real_minutes_subquery,
                Task.id == real_minutes_subquery.c.task_id
            )
        )

        return self.db.execute(query).all()

    def get_task_performance_group_data(self, year: Optional[int] = None, month: Optional[int] = None):
        real_hours_subquery = (
            self.db.query(
                RecordStopwatch.task_id,
                func.sum(RecordStopwatch.accumulated_duration).label('total_real_hours'),
                extract('year', RecordStopwatch.creation_date).label('year'),
                extract('month', RecordStopwatch.creation_date).label('month')
            )
            .group_by(RecordStopwatch.task_id, extract('year', RecordStopwatch.creation_date), extract('month', RecordStopwatch.creation_date))
            .subquery()
        )

        base_query = (
            select(
                Code.code,
                Code.description,
                Code.type,
                func.sum(func.coalesce(real_hours_subquery.c.total_real_hours, 0)).label('sum_hours'),
                func.sum(ProgrammingTask.real_quantity).label('sum_quantity'),
                case(
                    (func.sum(ProgrammingTask.real_quantity) != 0,
                     func.sum(func.coalesce(real_hours_subquery.c.total_real_hours, 0)) / func.sum(ProgrammingTask.real_quantity)
                    ),
                    else_=None
                ).label('avg_time_per_product'),
                Task.people,
                case(
                    (func.sum(ProgrammingTask.real_quantity) != 0,
                     (func.sum(func.coalesce(real_hours_subquery.c.total_real_hours, 0)) / func.sum(ProgrammingTask.real_quantity)) * Task.people
                    ),
                    else_=None
                ).label('final_metric')
            )
            .select_from(Code)
            .join(Task, Code.id == Task.code_id)
            .join(ProgrammingTask, Task.id == ProgrammingTask.task_id)
            .outerjoin(
                real_hours_subquery,
                and_(
                    Task.id == real_hours_subquery.c.task_id,
                    extract('year', ProgrammingTask.start_time) == real_hours_subquery.c.year,
                    extract('month', ProgrammingTask.start_time) == real_hours_subquery.c.month
                )
            )
        )

        if year is not None and month is not None:
            query = base_query.where(
                extract('year', ProgrammingTask.start_time) == year,
                extract('month', ProgrammingTask.start_time) == month
            ).group_by(extract('year', ProgrammingTask.start_time), extract('month', ProgrammingTask.start_time), Code.code, Code.description, Code.type, Task.people)
        else:
            query = base_query.group_by(Code.code, Code.description, Code.type, Task.people)

        return self.db.execute(query).all()

    def get_team_performance_data(self, start_date: date, end_date: date):
        real_minutes_subquery = (
            self.db.query(
                RecordStopwatch.task_id,
                func.date(RecordStopwatch.creation_date).label('record_date'),
                func.sum(RecordStopwatch.accumulated_duration * 60).label('total_real_minutes')
            )
            .group_by(RecordStopwatch.task_id, func.date(RecordStopwatch.creation_date))
            .subquery()
        )

        query = (
            self.db.query(
                Team.name,
                func.count(distinct(Programming.id)).label('total_days'),
                func.count(ProgrammingTask.task_id).label('total_tasks'),
                func.sum(case([(ProgrammingTask.is_completed == True, 1)], else_=0)).label('completed_tasks'),
                func.sum(Task.minutes).label('scheduled_minutes'),
                func.sum(func.coalesce(real_minutes_subquery.c.total_real_minutes, 0)).label('real_minutes'),
                func.avg(func.coalesce(real_minutes_subquery.c.total_real_minutes, 0)).label('avg_task_minutes')
            )
            .join(Programming, Team.id == Programming.team_id)
            .join(ProgrammingTask, Programming.id == ProgrammingTask.programming_id)
            .join(Task, ProgrammingTask.task_id == Task.id)
            .outerjoin(
                real_minutes_subquery,
                and_(
                    Task.id == real_minutes_subquery.c.task_id,
                    Programming.date == real_minutes_subquery.c.record_date
                )
            )
            .filter(
                Programming.date.between(start_date, end_date),
                Programming.status != ProgrammingStatus.cancelled
            )
            .group_by(Team.name)
            .order_by(Team.name)
        )

        return query.all()
