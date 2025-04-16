# app/adapters/outbound/security/auth_user_manager.py

from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.adapters.configuration.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
DEFAULT_EXPIRES_MIN = settings.ACCESS_TOKEN_USER_EXPIRE_MINUTOS


class UserAuthManager:
    """
    Gerenciador de autenticação JWT para usuários.
    """

    crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    class UserAuthManager:
        """JWT authentication manager for users"""

        crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        @classmethod
        def create_access_token(cls, subject: str, expires_delta: timedelta = None) -> str:
            """Create an access token with expiration"""
            if expires_delta is None:
                expires_delta = timedelta(minutes=DEFAULT_EXPIRES_MIN)

            expire = datetime.utcnow() + expires_delta
            payload = {
                "sub": str(subject),
                "exp": int(expire.timestamp()),
                "type": "access",
            }

            return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @classmethod
    def create_refresh_token(cls, subject: str) -> str:
        """Create a refresh token"""
        # Longer expiration for refresh tokens
        expires_delta = timedelta(days=7)
        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": str(subject),
            "exp": int(expire.timestamp()),
            "type": "refresh",
        }

        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @classmethod
    def verify_access_token(cls, token: str) -> dict:
        """Verify an access token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type.",
                )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
            )

    @classmethod
    def verify_refresh_token(cls, token: str) -> dict:
        """Verify a refresh token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type.",
                )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )

    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Retorna o hash da senha em texto plano.
        """
        return cls.crypt_context.hash(password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """
        Verifica se a senha em texto corresponde ao hash armazenado.
        """
        return cls.crypt_context.verify(plain_password, hashed_password)
