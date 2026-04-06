from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
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
    user = auth_service.register(db, body.full_name, body.email, body.password, body.phone, body.role)
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
    return auth_service.login(db, body.email, body.password)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    auth_service.forgot_password(db, body.email)
    # Always return the same response — prevents email enumeration
    return _ok(message="Si cet email existe, un code de réinitialisation a été envoyé.")


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, body.email, body.code, body.new_password)
    return _ok(message="Mot de passe réinitialisé avec succès.")
