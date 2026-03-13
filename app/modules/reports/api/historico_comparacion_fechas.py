from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.shared.db.session import get_db
from app.modules.reports.services.historico_comparacion_fechas import HistoricoComparacionFechasService
from app.modules.reports.schemas.historico_comparacion_fechas import (
    HistoricoComparacionFechasCreate, 
    HistoricoComparacionFechasUpdate, 
    HistoricoComparacionFechasOut
)
from app.shared.utils.core.dependencies import get_current_user
from app.modules.organization.models.user import User

router = APIRouter(prefix="/historico-comparacion-fechas", tags=["historico-comparacion-fechas"])


@router.post("/", response_model=HistoricoComparacionFechasOut, status_code=status.HTTP_201_CREATED)
def create_historico_fecha(
    fecha_data: HistoricoComparacionFechasCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo registro de fecha histórica.
    """
    service = HistoricoComparacionFechasService(db)
    
    try:
        created_record = service.create(fecha_data)
        return created_record
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating historico fecha record: {str(e)}"
        )


@router.post("/bulk", response_model=List[HistoricoComparacionFechasOut], status_code=status.HTTP_201_CREATED)
def create_multiple_historico_fechas(
    fechas_data: List[HistoricoComparacionFechasCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea múltiples registros de fechas históricas desde un array.
    """
    service = HistoricoComparacionFechasService(db)
    created_records = []
    
    try:
        for fecha_data in fechas_data:
            created_record = service.create(fecha_data)
            created_records.append(created_record)
        
        return created_records
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating historico fecha records: {str(e)}"
        )


@router.get("/", response_model=List[HistoricoComparacionFechasOut])
def get_all_historico_fechas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los registros de fechas históricas.
    """
    service = HistoricoComparacionFechasService(db)
    records = service.get_all()
    return records


@router.get("/{fecha_id}", response_model=HistoricoComparacionFechasOut)
def get_historico_fecha(
    fecha_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene un registro de fecha histórica por su ID.
    """
    service = HistoricoComparacionFechasService(db)
    record = service.get_by_id(fecha_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historico fecha record with id {fecha_id} not found"
        )
    
    return record


@router.put("/{fecha_id}", response_model=HistoricoComparacionFechasOut)
def update_historico_fecha(
    fecha_id: uuid.UUID,
    fecha_data: HistoricoComparacionFechasUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza un registro de fecha histórica existente.
    """
    service = HistoricoComparacionFechasService(db)
    
    try:
        updated_record = service.update(fecha_id, fecha_data)
        return updated_record
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating historico fecha record: {str(e)}"
        )


@router.delete("/{fecha_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_historico_fecha(
    fecha_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un registro de fecha histórica.
    """
    service = HistoricoComparacionFechasService(db)
    
    try:
        service.delete(fecha_id)
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting historico fecha record: {str(e)}"
        )



