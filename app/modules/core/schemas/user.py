import uuid
import re
from pydantic import BaseModel, Field, validator, EmailStr
from app.modules.core.models.role import UserRole
from app.modules.core.models.state import UserState
from app.modules.core.models.team import Team
from typing import List, Optional

class UserCreate(BaseModel):
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        description="Nombre de usuario único",
        example="john_doe"
    )
    password: str = Field(
        ..., 
        min_length=6,
        max_length=128,
        description="Contraseña (mínimo 6 caracteres)",
        example="mipassword123"
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="Rol del usuario en el sistema"
    )
    state: UserState = Field(
        default=UserState.ACTIVE,
        description="Estado del usuario"
    )
    teamIds: Optional[List[uuid.UUID]] = Field(
        default=[],
        description="Lista de IDs de equipos a los que pertenece el usuario"
    )

    @validator('username')
    def validate_username(cls, v):
        """Valida el formato del nombre de usuario"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('El nombre de usuario solo puede contener letras, números y guiones bajos')
        
        if v.lower() in ['admin', 'root', 'system', 'test', 'guest']:
            raise ValueError('Nombre de usuario no permitido')
        
        return v

    @validator('password')
    def validate_password(cls, v):
        """Valida la fortaleza de la contraseña"""
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        
        # Verificar contraseñas muy comunes
        common_passwords = [
            'password', '123456', 'qwerty', 'admin', 'letmein',
            'welcome', 'monkey', 'password123', 'admin123'
        ]
        if v.lower() in common_passwords:
            raise ValueError('La contraseña es demasiado común')
        
        return v

    @validator('teamIds')
    def validate_team_ids(cls, v):
        """Valida que no haya IDs duplicados"""
        if v is not None:
            unique_ids = list(set(v))
            if len(unique_ids) != len(v):
                raise ValueError('No se permiten IDs de equipo duplicados')
        return v

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "mipassword123",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": []
            }
        }

class UserOut(BaseModel):
    id: uuid.UUID = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    state: UserState = Field(default=UserState.ACTIVE, description="Estado del usuario")
    teamIds: Optional[List[uuid.UUID]] = Field(default=[], description="IDs de equipos")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": []
            }
        }

class UserUpdate(BaseModel):
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        description="Nombre de usuario único",
        example="john_doe"
    )
    password: Optional[str] = Field(
        None, 
        min_length=6,
        max_length=128,
        description="Contraseña (mínimo 6 caracteres, opcional para actualizaciones)",
        example="mipassword123"
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="Rol del usuario en el sistema"
    )
    state: UserState = Field(
        default=UserState.ACTIVE,
        description="Estado del usuario"
    )
    teamIds: Optional[List[uuid.UUID]] = Field(
        default=[],
        description="Lista de IDs de equipos a los que pertenece el usuario"
    )

    @validator('username')
    def validate_username(cls, v):
        """Valida el formato del nombre de usuario"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('El nombre de usuario solo puede contener letras, números y guiones bajos')
        
        if v.lower() in ['admin', 'root', 'system', 'test', 'guest']:
            raise ValueError('Nombre de usuario no permitido')
        
        # For updates, preserve the original casing
        return v

    @validator('password')
    def validate_password(cls, v):
        """Valida la fortaleza de la contraseña (solo si se proporciona)"""
        if v is None:
            return v
        
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        
        # Verificar contraseñas muy comunes
        common_passwords = [
            'password', '123456', 'qwerty', 'admin', 'letmein',
            'welcome', 'monkey', 'password123', 'admin123'
        ]
        if v.lower() in common_passwords:
            raise ValueError('La contraseña es demasiado común')
        
        return v

    @validator('teamIds')
    def validate_team_ids(cls, v):
        """Valida que no haya IDs duplicados"""
        if v is not None:
            unique_ids = list(set(v))
            if len(unique_ids) != len(v):
                raise ValueError('No se permiten IDs de equipo duplicados')
        return v

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "mipassword123",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": []
            }
        }

class UserStateUpdate(BaseModel):
    state: UserState

class User(BaseModel):
    id: uuid.UUID = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    state: UserState = Field(default=UserState.ACTIVE, description="Estado del usuario")

    class Config:
        from_attributes = True

class UsersPageOut(BaseModel):
    users: List[UserOut]
    total: int
