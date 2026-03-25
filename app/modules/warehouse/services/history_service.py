from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException
from app.modules.warehouse.repositories import history_repository
from app.modules.warehouse.models.history import WarehouseHistory, WarehouseHistoryType

def get_history(
    db: Session,
    lote: Optional[int] = None,
    code: Optional[str] = None,
    user: Optional[str] = None,
    history_type: Optional[WarehouseHistoryType] = None,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    date_str: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[WarehouseHistory]:
    """
    Process filters and fetch warehouse history.
    """
    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
            
    start_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha de inicio inválido. Use YYYY-MM-DD")

    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha de fin inválido. Use YYYY-MM-DD")

    return history_repository.find_all(
        db, 
        lote=lote, 
        code=code, 
        user=user, 
        history_type=history_type, 
        start_date=start_date,
        end_date=end_date,
        target_date=target_date, 
        skip=skip, 
        limit=limit
    )

def get_history_by_identifier(
    db: Session,
    identifier: str
) -> List[WarehouseHistory]:
    """
    Fetch history by lote or code identifier.
    """
    return history_repository.find_by_identifier(db, identifier)
