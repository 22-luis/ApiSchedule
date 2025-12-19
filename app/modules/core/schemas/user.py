import uuid
import re
import base64
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from sqlalchemy import LargeBinary

from app.modules.core.models.role import UserRole
from app.modules.core.models.state import UserState
from app.modules.core.models.team import Team
from typing import List, Optional, Union

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

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('El nombre de usuario solo puede contener letras, números y guiones bajos')
        
        if v.lower() in ['admin', 'root', 'system', 'test', 'guest']:
            raise ValueError('Nombre de usuario no permitido')
        
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        
        common_passwords = [
            'password', '123456', 'qwerty', 'admin', 'letmein',
            'welcome', 'monkey', 'password123', 'admin123'
        ]
        if v.lower() in common_passwords:
            raise ValueError('La contraseña es demasiado común')
        
        return v

    @field_validator('teamIds')
    @classmethod
    def validate_team_ids(cls, v):
        if v is not None:
            unique_ids = list(set(v))
            if len(unique_ids) != len(v):
                raise ValueError('No se permiten IDs de equipo duplicados')
        return v

    model_config = ConfigDict(
        from_attributes = True,
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "mipassword123",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": []
            }
        }
    )

class UserOut(BaseModel):
    id: uuid.UUID = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    state: UserState = Field(default=UserState.ACTIVE, description="Estado del usuario")
    teamIds: Optional[List[uuid.UUID]] = Field(default=[], description="IDs de equipos")
    signature: Optional[str] = Field(None, description="Firma del usuario")

    @field_validator('signature', mode='before')
    @classmethod
    def validate_signature(cls, v):
        if v is None:
            return None
        if isinstance(v, (bytes, bytearray, memoryview)):
            try:
                return base64.b64encode(bytes(v)).decode('utf-8')
            except Exception:
                return None
        return v

    model_config = ConfigDict(
        from_attributes = True,
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": [],
                "signature": None
            }
        }
    )

class UserUpdate(BaseModel):
    username: Optional[str] = Field(
        None, 
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
    role: Optional[UserRole] = Field(
        None,
        description="Rol del usuario en el sistema"
    )
    state: Optional[UserState] = Field(
        None,
        description="Estado del usuario"
    )
    teamIds: Optional[List[uuid.UUID]] = Field(
        None,
        description="Lista de IDs de equipos a los que pertenece el usuario"
    )
    signature: Optional[Union[str, bytes]] = Field(None, description="Firma del usuario")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if v is None:
            return v
            
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('El nombre de usuario solo puede contener letras, números y guiones bajos')
        
        if v.lower() in ['admin', 'root', 'system', 'test', 'guest']:
            raise ValueError('Nombre de usuario no permitido')
        
        # For updates, preserve the original casing
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if v is None:
            return v
        
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        
        # Verify common passwords
        common_passwords = [
            'password', '123456', 'qwerty', 'admin', 'letmein',
            'welcome', 'monkey', 'password123', 'admin123'
        ]
        if v.lower() in common_passwords:
            raise ValueError('La contraseña es demasiado común')
        
        return v

    @field_validator('teamIds')
    @classmethod
    def validate_team_ids(cls, v):
        if v is not None:
            unique_ids = list(set(v))
            if len(unique_ids) != len(v):
                raise ValueError('No se permiten IDs de equipo duplicados')
        return v

    @field_validator('signature', mode='before')
    @classmethod
    def validate_signature(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip():
            try:
                # Si ya es un Base64 válido, lo decodificamos a bytes
                return base64.b64decode(v)
            except Exception:
                # Si no es un Base64 válido pero es un string, lanzamos el error
                raise ValueError('La firma debe ser una cadena base64 válida')
        if isinstance(v, (bytes, bytearray, memoryview)):
            return bytes(v)
        return v

    model_config = ConfigDict(
        from_attributes = True,
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "mipassword123",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": [],
                "signature": None
            }
        }
    )

class UserStateUpdate(BaseModel):
    state: UserState

class User(BaseModel):
    id: uuid.UUID = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    state: UserState = Field(default=UserState.ACTIVE, description="Estado del usuario")

    model_config = ConfigDict(
        from_attributes = True
    )

class UsersPageOut(BaseModel):
    users: List[UserOut]
    total: int
