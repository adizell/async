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

    @classmethod
    def create_access_token(cls, subject: str, expires_delta: timedelta = None) -> str:
        """
        Cria um token JWT para o usuário autenticado.

        - `subject`: normalmente o UUID do usuário.
        - `expires_delta`: tempo de expiração customizado.
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=DEFAULT_EXPIRES_MIN)

        expire = datetime.utcnow() + expires_delta
        payload = {
            "sub": str(subject),
            "exp": int(expire.timestamp()),
            "type": "user",
        }

        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @classmethod
    def verify_access_token(cls, token: str) -> dict:
        """
        Verifica e decodifica um token JWT de usuário.

        Retorna o payload se for válido.
        Lança HTTP 401 se o token for inválido, expirado ou incorreto.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "user":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido: tipo incorreto.",
                )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado.",
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

    @classmethod
    def create_refresh_token(cls, subject: str, token_id: str, expires_delta: timedelta = None) -> str:
        if expires_delta is None:
            # Usar a configuração em vez de um valor fixo
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        """
        Cria um token JWT para refresh token.

        - `subject`: normalmente o UUID do usuário.
        - `token_id`: identificador único do token para controle.
        - `expires_delta`: tempo de expiração customizado.
        """
        if expires_delta is None:
            # Por padrão, refresh tokens duram 30 dias
            expires_delta = timedelta(days=30)

        expire = datetime.utcnow() + expires_delta
        payload = {
            "sub": str(subject),
            "exp": int(expire.timestamp()),
            "type": "refresh",
            "jti": token_id,  # JWT ID - identificador único para este token
        }

        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @classmethod
    def verify_refresh_token(cls, token: str) -> dict:
        """
        Verifica e decodifica um refresh token JWT.

        Retorna o payload se for válido.
        Lança HTTP 401 se o token for inválido, expirado ou incorreto.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido: não é um refresh token.",
                )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou expirado.",
            )
