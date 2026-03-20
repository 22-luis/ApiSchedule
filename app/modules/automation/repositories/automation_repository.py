from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.orders.models import order as order_model
from app.modules.programming.models.programming import Programming
from app.modules.organization.models.team import Team

class AutomationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_orders_by_lotes(self, lotes: List[int]):
        return self.db.query(order_model.Order).filter(order_model.Order.lote.in_(lotes)).all()

    def get_programming_by_id(self, programming_id: str):
        return self.db.query(Programming).filter(Programming.id == programming_id).first()

    def get_team_by_id(self, team_id: str):
        return self.db.query(Team).filter(Team.id == team_id).first()

    def save_notification(self, notification):
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
