"""Small JWT/password helpers for the prototype API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "customer_id": str(user.customer_id) if user.customer_id else None,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id = uuid.UUID(payload.get("sub", ""))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token user")
    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Allow synthetic demo requests, but never an invalid supplied token."""
    if credentials is None:
        return None
    return get_current_user(credentials, db)


def require_customer_owner(customer_id: uuid.UUID, current_user: User) -> None:
    if current_user.customer_id != customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="customer access denied")


def require_customer_access(
    customer_id: uuid.UUID | None = None,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Synthetic demo rows remain public; manual rows always require ownership."""
    if customer_id is None:
        return
    from app.database.models import Customer
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer and customer.data_source == "user_provided":
        if current_user is None or current_user.customer_id != customer_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="customer access denied")
