# app/test/routes/user_group/test_register_user_assigns_user_group.py

# Para Rodar o Script:
# pytest app/test/routes/user_group/test_register_user_assigns_user_group.py -v

import pytest
from app.application.dtos.user_dto import UserCreate
from app.application.use_cases.auth_use_cases import AsyncAuthService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_register_user_assigns_user_group(db_session: AsyncSession):
    service = AsyncAuthService(db_session)

    user_data = UserCreate(
        email="register_user_assigns_user_group@example.com",
        password="SenhaForte@123"
    )

    user = await service.register_user(user_data)
    await db_session.refresh(user)

    group_names = [group.name for group in user.groups]

    assert "user" in group_names, f"❌ Grupo 'user' não atribuído ao usuário {user.email}!"
    print(f"✅ Grupo 'user' atribuído corretamente para {user.email}.")
