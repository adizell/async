# app/adapters/outbound/security/permissions.py (async version)

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_session, get_permissions_current_user
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.domain.exceptions import PermissionDeniedException


def collect_user_permissions(user: User) -> set[str]:
    """
    Coleta todas as permissões de um usuário, incluindo permissões diretas
    e herdadas via grupos.
    """
    permissions = {perm.codename for perm in user.permissions}
    for group in user.groups:
        permissions.update(perm.codename for perm in group.permissions)
    return permissions


async def require_superuser(current_user: User = Depends(get_permissions_current_user)) -> User:
    """
    Valida se o usuário atual é superusuário.
    Lança PermissionDeniedException se não for.
    """
    if not current_user.is_superuser:
        raise PermissionDeniedException("Acesso permitido apenas a superusuários.")
    return current_user


def require_permission(permission_codename: str):
    """
    Retorna uma dependência que valida se o usuário autenticado possui uma
    permissão específica. Superusuários são automaticamente autorizados.

    Uso:
        @router.get(..., dependencies=[Depends(require_permission("add_pet"))])
    """

    async def permission_checker(
            current_user: User = Depends(get_permissions_current_user),
            db: AsyncSession = Depends(get_session),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        user_permissions = collect_user_permissions(current_user)

        if permission_codename not in user_permissions:
            raise PermissionDeniedException(f"Permissão '{permission_codename}' negada.")
        return current_user

    return permission_checker


def require_permission_or_superuser(permission_codename: str):
    """
    Valida se o usuário possui a permissão ou se é superusuário.
    """

    async def checker(current_user: User = Depends(get_permissions_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        user_permissions = collect_user_permissions(current_user)

        if permission_codename not in user_permissions:
            raise PermissionDeniedException(f"Permissão '{permission_codename}' negada.")
        return current_user

    return checker
