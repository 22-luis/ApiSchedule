from sqlalchemy.orm import Session
from app.modules.reports.models.compare import ProductionReport
from app.modules.reports.schemas.compare import CompareCreate, CompareUpdate, CompareOut
import uuid
from typing import Optional, List
from datetime import date

class CompareService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, compare_data: CompareCreate) -> ProductionReport:
        """
        Crea un nuevo registro de comparación.
        
        Args:
            compare_data: Datos para crear el registro (CompareCreate)
            
        Returns:
            ProductionReport: El registro creado
        """
        db_compare = ProductionReport(**compare_data.dict())
        self.db.add(db_compare)
        self.db.commit()
        self.db.refresh(db_compare)
        return db_compare

    def update(self, compare_id: uuid.UUID, compare_data: CompareUpdate) -> ProductionReport:
        """
        Actualiza un registro de comparación existente.
        
        Args:
            compare_id: ID del registro a actualizar
            compare_data: Datos para actualizar (CompareUpdate)
            
        Returns:
            ProductionReport: El registro actualizado
            
        Raises:
            ValueError: Si el registro no existe
        """
        db_compare = self.db.query(ProductionReport).filter(ProductionReport.id == compare_id).first()
        if not db_compare:
            raise ValueError(f"Compare record with id {compare_id} not found")
        
        update_data = compare_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_compare, field, value)
        
        self.db.commit()
        self.db.refresh(db_compare)
        return db_compare

    def delete(self, compare_id: uuid.UUID) -> bool:
        """
        Elimina un registro de comparación.
        
        Args:
            compare_id: ID del registro a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
            
        Raises:
            ValueError: Si el registro no existe
        """
        db_compare = self.db.query(ProductionReport).filter(ProductionReport.id == compare_id).first()
        if not db_compare:
            raise ValueError(f"Compare record with id {compare_id} not found")
        
        self.db.delete(db_compare)
        self.db.commit()
        return True

    def get_by_id(self, compare_id: uuid.UUID) -> Optional[ProductionReport]:
        """
        Obtiene un registro de comparación por su ID.
        
        Args:
            compare_id: ID del registro
            
        Returns:
            ProductionReport o None si no existe
        """
        return self.db.query(ProductionReport).filter(ProductionReport.id == compare_id).first()

    def get_by_date(self, compare_date: date) -> List[ProductionReport]:
        """
        Obtiene todos los registros de comparación que tengan una fecha específica.
        
        Args:
            compare_date: Fecha a filtrar
            
        Returns:
            Lista de ProductionReport que coinciden con la fecha
        """
        return self.db.query(ProductionReport).filter(ProductionReport.compare_date == compare_date).all()



