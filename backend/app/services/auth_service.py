import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.otp_code import OtpCode
from app.models.subscription import OwnerSubscription, SubscriptionPlan
from app.core.security import hash_password, verify_password, create_access_token
from app.services.email_service import send_otp_email


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def _create_otp(db: Session, user_id: int, purpose: str) -> str:
    # Invalidate any existing unused OTPs for same user + purpose
    db.query(OtpCode).filter(
        OtpCode.user_id == user_id,
        OtpCode.purpose == purpose,
        OtpCode.used_at == None,
    ).delete()

    code = _generate_otp()
    otp = OtpCode(
        user_id=user_id,
        code=code,
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.add(otp)
    db.commit()
    return code


def _assign_starter_plan(db: Session, owner_id: int) -> None:
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "starter").first()
    if not plan:
        return  # Plans not seeded yet — skip
    sub = OwnerSubscription(
        owner_id=owner_id,
        plan_id=plan.id,
        started_at=datetime.now(timezone.utc),
        expires_at=None,  # Starter has no expiry
        is_active=True,
    )
    db.add(sub)
    db.commit()


def register(db: Session, full_name: str, email: str, password: str, phone: str | None, role: str = "OWNER") -> User:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email",
        )
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        phone=phone,
        is_verified=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # US-043: auto-assign Starter plan for owners only
    if role == "OWNER":
        _assign_starter_plan(db, user.id)

    # Send email verification OTP
    code = _create_otp(db, user.id, "EMAIL_VERIFY")
    send_otp_email(email, code, "EMAIL_VERIFY")

    return user


def verify_email(db: Session, email: str, code: str) -> None:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    otp = (
        db.query(OtpCode)
        .filter(
            OtpCode.user_id == user.id,
            OtpCode.purpose == "EMAIL_VERIFY",
            OtpCode.code == code,
            OtpCode.used_at == None,
            OtpCode.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    if not otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code invalide ou expiré")

    otp.used_at = datetime.now(timezone.utc)
    user.is_verified = True
    db.commit()


def login(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez vérifier votre email avant de vous connecter",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role}


def forgot_password(db: Session, email: str) -> None:
    # Always return success — prevents email enumeration
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return
    code = _create_otp(db, user.id, "PASSWORD_RESET")
    send_otp_email(email, code, "PASSWORD_RESET")


def reset_password(db: Session, email: str, code: str, new_password: str) -> None:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code invalide ou expiré")

    otp = (
        db.query(OtpCode)
        .filter(
            OtpCode.user_id == user.id,
            OtpCode.purpose == "PASSWORD_RESET",
            OtpCode.code == code,
            OtpCode.used_at == None,
            OtpCode.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    if not otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code invalide ou expiré")

    otp.used_at = datetime.now(timezone.utc)
    user.password_hash = hash_password(new_password)
    db.commit()
