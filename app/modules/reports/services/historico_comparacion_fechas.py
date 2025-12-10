from sqlalchemy.orm import Session
from app.modules.reports.models.historico_comparacion_fechas import HistoricoComparacionFechas
from app.modules.reports.schemas.historico_comparacion_fechas import (
    HistoricoComparacionFechasCreate, 
    HistoricoComparacionFechasUpdate, 
    HistoricoComparacionFechasOut
)
import uuid
from typing import Optional

class HistoricoComparacionFechasService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, fecha_data: HistoricoComparacionFechasCreate) -> HistoricoComparacionFechas:
        """
        Crea un nuevo registro de fecha histórica.
        
        Args:
            fecha_data: Datos para crear el registro (HistoricoComparacionFechasCreate)
            
        Returns:
            HistoricoComparacionFechas: El registro creado
        """
        db_fecha = HistoricoComparacionFechas(**fecha_data.dict())
        self.db.add(db_fecha)
        self.db.commit()
        self.db.refresh(db_fecha)
        return db_fecha

    def update(self, fecha_id: uuid.UUID, fecha_data: HistoricoComparacionFechasUpdate) -> HistoricoComparacionFechas:
        """
        Actualiza un registro de fecha histórica existente.
        
        Args:
            fecha_id: ID del registro a actualizar
            fecha_data: Datos para actualizar (HistoricoComparacionFechasUpdate)
            
        Returns:
            HistoricoComparacionFechas: El registro actualizado
            
        Raises:
            ValueError: Si el registro no existe
        """
        db_fecha = self.db.query(HistoricoComparacionFechas).filter(HistoricoComparacionFechas.id == fecha_id).first()
        if not db_fecha:
            raise ValueError(f"Historico comparacion fecha with id {fecha_id} not found")
        
        update_data = fecha_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_fecha, field, value)
        
        self.db.commit()
        self.db.refresh(db_fecha)
        return db_fecha

    def delete(self, fecha_id: uuid.UUID) -> bool:
        """
        Elimina un registro de fecha histórica.
        
        Args:
            fecha_id: ID del registro a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
            
        Raises:
            ValueError: Si el registro no existe
        """
        db_fecha = self.db.query(HistoricoComparacionFechas).filter(HistoricoComparacionFechas.id == fecha_id).first()
        if not db_fecha:
            raise ValueError(f"Historico comparacion fecha with id {fecha_id} not found")
        
        self.db.delete(db_fecha)
        self.db.commit()
        return True

    def get_by_id(self, fecha_id: uuid.UUID) -> Optional[HistoricoComparacionFechas]:
        """
        Obtiene un registro de fecha histórica por su ID.
        
        Args:
            fecha_id: ID del registro
            
        Returns:
            HistoricoComparacionFechas o None si no existe
        """
        return self.db.query(HistoricoComparacionFechas).filter(HistoricoComparacionFechas.id == fecha_id).first()

    def get_all(self) -> list[HistoricoComparacionFechas]:
        """
        Obtiene todos los registros de fechas históricas.
        
        Returns:
            Lista de HistoricoComparacionFechas
        """
        return self.db.query(HistoricoComparacionFechas).all()



