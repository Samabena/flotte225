from datetime import datetime
from pydantic import BaseModel, field_validator


class DriverCreate(BaseModel):
    full_name: str
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Le nom d'utilisateur est requis")
        if "@" in v:
            raise ValueError("Le nom d'utilisateur ne peut pas contenir @")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le nom complet est requis")
        return v.strip()


class DriverStatusUpdate(BaseModel):
    is_disabled: bool


class DriverPasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        return v


class DriverResponse(BaseModel):
    id: int
    full_name: str
    username: str
    is_disabled: bool
    driving_status: bool
    created_at: datetime

    model_config = {"from_attributes": True}
