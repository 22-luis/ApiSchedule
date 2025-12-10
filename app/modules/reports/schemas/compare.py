import uuid
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

class CompareCreate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    tipo: Optional[str] = None
    tiempo: Optional[Decimal] = None
    total_tiempo_real: Optional[Decimal] = None
    diferencia: Optional[Decimal] = None
    compare_date: Optional[date] = None
    numero_personas: Optional[int] = None

class CompareInputItem(BaseModel):
    """Schema para recibir datos del frontend en formato JSON"""
    codigo: Optional[str] = Field(None, alias="codigo")
    descripcion: Optional[str] = Field(None, alias="descripcion")
    tipo: Optional[str] = Field(None, alias="tipo")
    numeroPersonas: Optional[int] = Field(None, alias="numeroPersonas")
    totalTiempoReal: Optional[float] = Field(None, alias="totalTiempoReal")
    unitsReq: Optional[float] = Field(None, alias="unitsReq")
    diferencia: Optional[float] = Field(None, alias="diferencia")
    compareDate: Optional[datetime] = Field(None, alias="compareDate")
    numeroPersonas: Optional[int] = Field(None, alias="numeroPersonas")
    
    @validator('compareDate', pre=True)
    def parse_date(cls, v):
        if isinstance(v, str):
            try:
                # Intentar parsear como datetime
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except:
                try:
                    return datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ')
                except:
                    return datetime.strptime(v, '%Y-%m-%d')
        return v
    
    def to_compare_create(self) -> CompareCreate:
        """Convierte el formato de entrada al formato del modelo"""
        compare_date = None
        if self.compareDate:
            if isinstance(self.compareDate, datetime):
                compare_date = self.compareDate.date()
            elif isinstance(self.compareDate, date):
                compare_date = self.compareDate
        
        tiempo = None
        if self.unitsReq is not None:
            try:
                tiempo = Decimal(str(self.unitsReq))
            except (ValueError, TypeError):
                tiempo = None
        
        total_tiempo_real = None
        if self.totalTiempoReal is not None:
            try:
                total_tiempo_real = Decimal(str(self.totalTiempoReal))
            except (ValueError, TypeError):
                total_tiempo_real = None
        
        diferencia = None
        if self.diferencia is not None:
            try:
                diferencia = Decimal(str(self.diferencia))
            except (ValueError, TypeError):
                diferencia = None
        
        return CompareCreate(
            code=self.codigo,
            description=self.descripcion,
            tipo=self.tipo,
            tiempo=tiempo,
            total_tiempo_real=total_tiempo_real,
            diferencia=diferencia,
            compare_date=compare_date
        )
    
    class Config:
        allow_population_by_field_name = True

class CompareUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    tipo: Optional[str] = None
    tiempo: Optional[Decimal] = None
    total_tiempo_real: Optional[Decimal] = None
    diferencia: Optional[Decimal] = None
    compare_date: Optional[date] = None

class CompareOut(BaseModel):
    id: uuid.UUID
    code: Optional[str] = None
    description: Optional[str] = None
    tipo: Optional[str] = None
    tiempo: Optional[Decimal] = None
    total_tiempo_real: Optional[Decimal] = None
    diferencia: Optional[Decimal] = None
    compare_date: Optional[date] = None
    numero_personas: Optional[int] = None

    class Config:
        from_attributes = True

