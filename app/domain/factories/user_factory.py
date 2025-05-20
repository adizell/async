# app/domain/factories/user_factory.py

from datetime import datetime, timezone
import uuid
from app.application.dtos.user_dto import UserCreate
from app.domain.models.user_domain_model import User as DomainUser


class UserFactory:
    """
    Factory para criação de objetos do domínio User.
    """

    @staticmethod
    def create_new_user(user_data: UserCreate, hashed_password: str) -> DomainUser:
        """
        Cria um novo objeto de domínio User a partir dos dados de entrada.

        Args:
            user_data: DTO com dados para criação
            hashed_password: Senha já criptografada

        Returns:
            DomainUser: Objeto de domínio User
        """
        return DomainUser(
            id=uuid.uuid4(),
            email=user_data.email,
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            groups=[],
            permissions=[]
        )
