from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.subscription import OwnerSubscription, SubscriptionPlan

bearer_scheme = HTTPBearer()


def _get_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: int = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")
    return user


def get_current_user(user: User = Depends(_get_user_from_token)) -> User:
    return user


def get_current_owner(user: User = Depends(_get_user_from_token)) -> User:
    if user.role != "OWNER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux propriétaires")
    return user


def get_current_driver(user: User = Depends(_get_user_from_token)) -> User:
    if user.role != "DRIVER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux chauffeurs")
    return user


def get_admin_user(user: User = Depends(_get_user_from_token)) -> User:
    if user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")
    return user


def require_plan(*plan_names: str):
    """Dependency factory — blocks if owner's active plan is not in plan_names."""

    def _check(
        owner: User = Depends(get_current_owner),
        db: Session = Depends(get_db),
    ) -> User:
        sub = (
            db.query(OwnerSubscription)
            .filter(OwnerSubscription.owner_id == owner.id, OwnerSubscription.is_active == True)
            .first()
        )
        if not sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Aucun abonnement actif")
        plan = db.get(SubscriptionPlan, sub.plan_id)
        if not plan or plan.name not in plan_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cette fonctionnalité nécessite un abonnement {' ou '.join(plan_names)}",
            )
        return owner

    return _check
