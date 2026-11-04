from datetime import datetime, timedelta, timezone
import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
<<<<<<< HEAD
from sqlalchemy import select
=======
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import User

ALGORITHM = "HS256"
bearer = HTTPBearer(auto_error=False)

<<<<<<< HEAD

def _dev_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == "dev@grupoepa.local"))
    if user is None:
        user = User(email="dev@grupoepa.local", display_name="Desenvolvimento", role="ADMIN", active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


=======
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "email": user.email, "role": user.role,
               "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

<<<<<<< HEAD

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if settings.auth_mode.lower() == "development":
        if credentials is None:
            return _dev_user(db)
        try:
            payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub", "0"))
        except (InvalidTokenError, ValueError, TypeError):
            return _dev_user(db)
        user = db.get(User, user_id)
        if not user or not user.active:
            return _dev_user(db)
        return user

=======
def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária.")
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except (InvalidTokenError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    user = db.get(User, user_id)
    if not user or not user.active:
<<<<<<< HEAD
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    return user


=======
        raise HTTPException(status_code=401, detail="Usuário inativo ou não encontrado.")
    return user

>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Você não tem permissão para esta operação.")
        return user
    return dependency
