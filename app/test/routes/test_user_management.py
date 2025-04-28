# app/test/routes/test_user_management.py

# Para Rodar o Script:
# pytest app/test/routes/test_user_management.py -v

import pytest
from sqlalchemy import select, delete
from app.adapters.outbound.persistence.models.user_model import User


# Helpers ────────────────────────────────────────────────────────────────────
def superuser_data(email="superuser_test@example.com"):
    return {"email": email, "password": "StrongP@ssword123"}


def common_user_data(email="commonuser_test@example.com"):
    return {"email": email, "password": "StrongP@ssword123"}


# ────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_user_deactivate(async_client, db_session, test_client_token):
    """Superusuário desativa usuário comum."""
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager

    headers = {"Authorization": f"Bearer {test_client_token}"}

    # e‑mails fixos para este teste
    super_email = "superuser_deactivate_test@example.com"
    common_email = "commonuser_deactivate_test@example.com"

    # limpeza
    await db_session.execute(delete(User).where(User.email.in_([super_email, common_email])))
    await db_session.commit()

    # 1) registra superuser (ainda sem flag)
    # Usar o serviço de registro que já faz o hash da senha
    await async_client.post("/api/v1/auth/register",
                            json=superuser_data(super_email),
                            headers=headers)

    # 2) marca como superuser direto no BD
    stmt = select(User).where(User.email == super_email)
    super_user = (await db_session.execute(stmt)).scalars().first()
    super_user.is_superuser = True
    await db_session.commit()

    # 3) login para pegar token de superuser
    login_resp = await async_client.post("/api/v1/auth/login",
                                         json=superuser_data(super_email),
                                         headers=headers)
    super_token = login_resp.json()["access_token"]
    sup_headers = {"Authorization": f"Bearer {super_token}"}

    # 4) registra usuário comum
    await async_client.post("/api/v1/auth/register",
                            json=common_user_data(common_email),
                            headers=headers)

    # 5) busca id do usuário comum
    common_user = (await db_session.execute(
        select(User).where(User.email == common_email))
                   ).scalars().first()
    common_id = str(common_user.id)

    # 6) superuser desativa
    resp = await async_client.delete(f"/api/v1/user/deactivate/{common_id}",
                                     headers=sup_headers)
    assert resp.status_code == 200, resp.text

    # 7) confirma no BD (forçando reload)
    is_active = (await db_session.execute(
        select(User.is_active)
        .where(User.id == common_user.id)
        .execution_options(populate_existing=True))
                 ).scalar_one()
    assert is_active is False, "Usuário não foi desativado no banco"


# ────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_user_reactivate(async_client, db_session, test_client_token):
    """Superusuário reativa usuário comum desativado."""
    headers = {"Authorization": f"Bearer {test_client_token}"}

    super_email = "superuser_reactivate_test@example.com"
    common_email = "commonuser_reactivate_test@example.com"

    await db_session.execute(delete(User).where(User.email.in_([super_email, common_email])))
    await db_session.commit()

    # superuser
    await async_client.post("/api/v1/auth/register",
                            json=superuser_data(super_email),
                            headers=headers)
    super_user = (await db_session.execute(
        select(User).where(User.email == super_email))
                  ).scalars().first()
    super_user.is_superuser = True
    await db_session.commit()

    login_resp = await async_client.post("/api/v1/auth/login",
                                         json=superuser_data(super_email),
                                         headers=headers)
    sup_headers = {"Authorization": f"Bearer " + login_resp.json()["access_token"]}

    # usuário comum
    await async_client.post("/api/v1/auth/register",
                            json=common_user_data(common_email),
                            headers=headers)
    common_user = (await db_session.execute(
        select(User).where(User.email == common_email))
                   ).scalars().first()
    common_id = str(common_user.id)

    # desativa direto no banco para preparar o teste
    common_user.is_active = False
    await db_session.commit()

    # reativa via endpoint
    resp = await async_client.post(f"/api/v1/user/reactivate/{common_id}",
                                   headers=sup_headers)
    assert resp.status_code == 200, resp.text

    # confirma no BD
    is_active = (await db_session.execute(
        select(User.is_active)
        .where(User.id == common_user.id)
        .execution_options(populate_existing=True))
                 ).scalar_one()
    assert is_active is True, "Usuário não foi reativado no banco"
