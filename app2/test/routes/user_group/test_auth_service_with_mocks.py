# app/test/routes/user_group/test_auth_service_with_mocks.py

# Para rodar o arquivo
# pytest app/test/routes/user_group/test_auth_service_with_mocks.py -v

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.application.use_cases.auth_use_cases import AsyncAuthService
from app.application.dtos.user_dto import UserCreate, TokenData


@pytest.mark.asyncio
async def test_register_user_with_mocks():
    """
    Testa o registro de usuário usando mocks para isolar dependências.
    """
    mock_db_session = AsyncMock()

    # Corrigir mocks de execute().unique().scalar_one_or_none()
    mock_group = MagicMock()
    mock_group.name = "user"

    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = mock_group

    mock_result = MagicMock()
    mock_result.unique.return_value = mock_scalar

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with patch('app.application.use_cases.auth_use_cases.user_repository') as mock_user_repo:
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.id = uuid.uuid4()
        mock_user.groups = []

        mock_user_repo.create = AsyncMock(return_value=mock_user)
        mock_user_repo.from_domain.return_value = mock_user
        mock_user_repo.to_domain.return_value = mock_user

        with patch('app.application.use_cases.auth_use_cases.UserAuthManager.hash_password',
                   new_callable=AsyncMock) as mock_hash:
            mock_hash.return_value = "hashed_password"

            service = AsyncAuthService(mock_db_session)
            user_data = UserCreate(email="test@example.com", password="StrongP@ssword123")

            result = await service.register_user(user_data)

            assert result is not None
            assert result.email == "test@example.com"
            assert mock_hash.called
            assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_login_user_with_mocks():
    """
    Testa o login de usuário usando mocks.
    """
    mock_db_session = AsyncMock()

    with patch('app.application.use_cases.auth_use_cases.user_repository') as mock_user_repo:
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_active = True

        mock_user_repo.authenticate = AsyncMock(return_value=mock_user)

        with patch('app.application.use_cases.auth_use_cases.UserAuthManager') as mock_auth_manager:
            mock_auth_manager.create_access_token = AsyncMock(return_value="fake_access_token")
            mock_auth_manager.create_refresh_token = AsyncMock(return_value="fake_refresh_token")

            service = AsyncAuthService(mock_db_session)
            user_data = UserCreate(email="test@example.com", password="StrongP@ssword123")

            result = await service.login_user(user_data)

            assert isinstance(result, TokenData)
            assert result.access_token == "fake_access_token"
            assert result.refresh_token == "fake_refresh_token"
            assert mock_user_repo.authenticate.called
