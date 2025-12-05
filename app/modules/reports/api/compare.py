from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.shared.db.session import get_db
from app.modules.reports.services.compare import CompareService
from app.modules.reports.schemas.compare import (
    CompareCreate, 
    CompareUpdate, 
    CompareOut,
    CompareInputItem
)
from app.shared.utils.core.dependencies import get_current_user
from app.modules.core.models.user import User

router = APIRouter(prefix="/compare", tags=["compare-reports"])


@router.post("/", response_model=List[CompareOut], status_code=status.HTTP_201_CREATED)
def create_compare_records(
    data: List[CompareInputItem],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea múltiples registros de comparación desde un array JSON.
    
    Recibe un array de objetos con el formato:
    - codigo: código del producto
    - descripcion: descripción del producto
    - tipo: tipo de producto
    - numeroPersonas: número de personas (no se guarda en el modelo)
    - totalTiempoReal: tiempo real utilizado
    - unitsReq: tiempo estimado (se mapea a tiempo)
    - diferencia: diferencia calculada
    - compareDate: fecha de comparación
    """
    service = CompareService(db)
    created_records = []
    
    try:
        for item in data:
            compare_data = item.to_compare_create()
            created_record = service.create(compare_data)
            created_records.append(created_record)
        
        return created_records
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating compare records: {str(e)}"
        )


@router.get("/", response_model=List[CompareOut])
def get_all_compare_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los registros de comparación.
    """
    from app.modules.reports.models.compare import ProductionReport
    
    records = db.query(ProductionReport).all()
    return records


@router.get("/{compare_id}", response_model=CompareOut)
def get_compare_record(
    compare_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene un registro de comparación por su ID.
    """
    service = CompareService(db)
    record = service.get_by_id(compare_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compare record with id {compare_id} not found"
        )
    
    return record


@router.put("/{compare_id}", response_model=CompareOut)
def update_compare_record(
    compare_id: uuid.UUID,
    compare_data: CompareUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza un registro de comparación existente.
    """
    service = CompareService(db)
    
    try:
        updated_record = service.update(compare_id, compare_data)
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
            detail=f"Error updating compare record: {str(e)}"
        )


@router.delete("/{compare_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_compare_record(
    compare_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un registro de comparación.
    """
    service = CompareService(db)
    
    try:
        service.delete(compare_id)
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
            detail=f"Error deleting compare record: {str(e)}"
        )

