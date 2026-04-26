from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer()


def _get_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: int = int(payload["sub"])
    except (PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable"
        )
    if user.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte a été désactivé. Contactez votre responsable.",
        )
    return user


def get_current_user(user: User = Depends(_get_user_from_token)) -> User:
    return user


def get_current_owner(user: User = Depends(_get_user_from_token)) -> User:
    if user.role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux propriétaires",
        )
    return user


def get_current_driver(user: User = Depends(_get_user_from_token)) -> User:
    if user.role != "DRIVER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux chauffeurs"
        )
    return user


def get_admin_user(user: User = Depends(_get_user_from_token)) -> User:
    if user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return user


def require_plan(*plan_names: str):
    # Subscription tiering deferred — all owners have equal access for now.
    # See docs/plans/subscription-tiering-deferred.md for re-implementation plan.
    return get_current_owner
