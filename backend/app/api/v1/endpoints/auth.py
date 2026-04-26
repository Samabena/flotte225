from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    VerifyEmailRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register(
        db, body.full_name, body.email, body.password, body.phone, body.company_name
    )
    return _ok(
        data={"id": user.id, "email": user.email},
        message="Compte créé. Vérifiez votre email pour activer votre compte.",
    )


@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    auth_service.verify_email(db, body.email, body.code)
    return _ok(message="Email vérifié. Vous pouvez maintenant vous connecter.")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login(db, body.identifier, body.password)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    auth_service.forgot_password(db, body.email)
    # Always return the same response — prevents email enumeration
    return _ok(message="Si cet email existe, un code de réinitialisation a été envoyé.")


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, body.email, body.code, body.new_password)
    return _ok(message="Mot de passe réinitialisé avec succès.")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.patch("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated user changes their own password."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )
    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit contenir au moins 6 caractères",
        )
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    return _ok(message="Mot de passe modifié avec succès.")
