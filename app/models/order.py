from sqlalchemy import Column, String, Enum, Integer, DateTime
from pydantic import BaseModel
from app.models.state import OrderState

class Order(BaseModel):
    id = Column(String, primary_key=True)
    lot = Column(Integer)
    code = Column(String)
    state = Column(Enum(OrderState))
    description = Column(String)
    amount = Column(Integer)
    bin = Column(Integer)
    created_at = Column(DateTime)