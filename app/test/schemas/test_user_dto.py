# app/test/schemas/test_user_dto.py

# Rodar Script
# pytest app/test/schemas/test_user_dto.py

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from pydantic import ValidationError
from app.application.dtos.user_dto import (
    UserCreate,
    UserOutput,
    UserSelfUpdate,
    UserUpdate,
    TokenData,
    RefreshTokenRequest,
)


def test_user_create_valid():
    user = UserCreate(
        email="validuser@example.com",
        password="StrongPassword123!"
    )
    assert user.email == "validuser@example.com"
    assert user.password == "StrongPassword123!"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(
            email="invalidemail",  # inválido!
            password="StrongPassword123"
        )


def test_user_create_invalid_password():
    with pytest.raises(ValidationError):
        UserCreate(
            email="validuser@example.com",
            password="123"  # menor que 6 caracteres
        )


def test_user_output_serialization():
    user = UserOutput(
        id=uuid4(),
        email="user@example.com",
        is_active=True,
        created_at=datetime.utcnow(),
        is_superuser=False,
        updated_at=None
    )
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)


def test_user_self_update_partial_update():
    update_data = UserSelfUpdate(email="newemail@example.com")
    assert update_data.email == "newemail@example.com"
    assert update_data.password is None


def test_user_update_admin_update():
    update_data = UserUpdate(is_active=False, is_superuser=True)
    assert update_data.is_active is False
    assert update_data.is_superuser is True


def test_token_data_validation():
    token_data = TokenData(
        access_token="access.jwt.token",
        refresh_token="refresh.jwt.token",
        expires_at=datetime.utcnow() + timedelta(minutes=30)
    )
    assert isinstance(token_data.expires_at, datetime)


def test_refresh_token_request_validation():
    refresh = RefreshTokenRequest(
        refresh_token="refresh.jwt.token"
    )
    assert refresh.refresh_token == "refresh.jwt.token"
