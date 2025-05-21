# app/adapters/inbound/api/v1/endpoints/sync_endpoint.py

"""
Endpoints para sincronização entre ambientes offline e online.

Este módulo implementa os endpoints responsáveis por sincronizar dados entre dispositivos offline e a API do servidor,
com suporte a estratégias de resolução de conflitos.

Fluxo de sincronização:
- Quando um dispositivo que esteve offline volta a se conectar, ele envia suas alterações para o servidor.
- O servidor compara os registros com base no campo `updated_at`.
- A estratégia padrão é "latest_wins", onde vence a versão mais recente do dado, comparando timestamps.

Estratégias de resolução de conflito:
- latest_wins: prevalece o dado com o `updated_at` mais recente (padrão).
- server_wins: o servidor sempre prevalece, ignorando alterações locais.
- client_wins: o cliente sempre prevalece, mesmo que o servidor tenha mudanças mais recentes.

Vantagens:
- Automatização da resolução de conflitos baseada em critérios objetivos.
- Prioridade para alterações mais recentes, evitando perda de dados atualizados.
- Flexibilidade para customizar estratégias por tipo de entidade ou campo.

Funcionalidades adicionais:
- Detecção de conflitos em nível de campo.
- Estratégias distintas por campo, permitindo granularidade na sincronização.
- Suporte para tratamento especial de campos sensíveis, que requerem lógica de resolução específica.

Esses endpoints são fundamentais para garantir integridade de dados e consistência em ambientes que operam com conectividade intermitente.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_db, get_permissions_current_user
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.shared.utils.datetime_utils import DateTimeUtil
from app.shared.utils.sync_manager import SyncEndpoint, SyncManager, ConflictResolutionStrategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["Synchronization"])


@router.get(
    "/timestamp",
    summary="Get current server timestamp",
    description="Returns the current server timestamp for synchronization."
)
async def get_server_timestamp():
    """
    Get the current server timestamp for synchronization.

    Returns:
        JSON with current UTC and local timestamp
    """
    now_utc = DateTimeUtil.utcnow()
    now_local = DateTimeUtil.localnow()

    return {
        "timestamp_utc": DateTimeUtil.format_iso(now_utc),
        "timestamp_local": DateTimeUtil.format_iso(now_local),
        "timezone": "America/Sao_Paulo"
    }


@router.get(
    "/entities/{entity_type}",
    summary="Get entities modified since timestamp",
    description="Returns entities that have been modified since the specified timestamp."
)
async def get_modified_entities(
        entity_type: str,
        last_sync: Optional[datetime] = Query(None, description="Timestamp of last synchronization (ISO 8601 format)"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Get entities that have been modified since the specified timestamp.

    Args:
        entity_type: Type of entity to synchronize
        last_sync: Timestamp of last synchronization
        db: Database session
        current_user: Authenticated user

    Returns:
        JSON with synchronized entities and metadata
    """
    try:
        # Exemplo simplificado - na implementação real, você teria
        # uma factory ou mapeamento para diferentes tipos de entidade
        from sqlalchemy import select
        from app.adapters.outbound.persistence.models.user_group.user_model import User

        entities: List[Dict[str, Any]] = []

        if entity_type == "users":
            # Verificar permissões
            if not current_user.is_superuser and not current_user.has_permission("list_users"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to sync user data"
                )

            # Consultar usuários atualizados desde last_sync
            query = select(User)

            if last_sync:
                query = query.where(User.updated_at >= last_sync)

            result = await db.execute(query)
            users = result.scalars().all()

            # Converter para formato de resposta
            for user in users:
                entities.append({
                    "id": str(user.id),
                    "email": user.email,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "created_at": DateTimeUtil.format_iso(DateTimeUtil.from_storage(user.created_at)),
                    "updated_at": DateTimeUtil.format_iso(DateTimeUtil.from_storage(user.updated_at))
                    if user.updated_at else None
                })

        # Preparar resposta padrão
        return SyncEndpoint.prepare_sync_response(
            updated_since=last_sync,
            items=entities,
            server_timestamp=DateTimeUtil.utcnow()
        )

    except Exception as e:
        logger.exception(f"Error during sync of {entity_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error synchronizing {entity_type}: {str(e)}"
        )


@router.post(
    "/entities/{entity_type}",
    summary="Synchronize client changes",
    description="Sync changes from client to server with conflict resolution."
)
async def sync_client_changes(
        entity_type: str,
        changes: List[Dict[str, Any]] = Body(..., description="Client changes to synchronize"),
        conflict_strategy: str = Query(
            "latest_wins",
            description="Strategy for conflict resolution: server_wins, client_wins, latest_wins"
        ),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Synchronize changes from client to server.

    Args:
        entity_type: Type of entity to synchronize
        changes: List of changed entities from client
        conflict_strategy: Strategy for resolving conflicts
        db: Database session
        current_user: Authenticated user

    Returns:
        JSON with synchronization results
    """
    # Converter estratégia de conflito
    strategy = ConflictResolutionStrategy.LATEST_WINS
    if conflict_strategy == "server_wins":
        strategy = ConflictResolutionStrategy.SERVER_WINS
    elif conflict_strategy == "client_wins":
        strategy = ConflictResolutionStrategy.CLIENT_WINS

    try:
        # Exemplo simplificado para usuários
        if entity_type == "users":
            # Verificar permissões
            if not current_user.is_superuser and not current_user.has_permission("manage_users"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to update user data"
                )

            # Resultados
            results = []
            conflicts = []

            # Processar cada mudança
            for change in changes:
                user_id = change.get("id")
                if not user_id:
                    conflicts.append({
                        "error": "Missing ID field",
                        "change": change
                    })
                    continue

                # Buscar usuário no banco
                from app.adapters.outbound.persistence.repositories.user_repository import user_repository
                server_user = await user_repository.get(db, id=user_id)

                if server_user:
                    # Existe - atualizar com estratégia de conflito
                    # Implementação completa envolveria criar objetos de domínio,
                    # detectar conflitos, e aplicar a estratégia selecionada

                    # Versão simplificada direta:
                    update_data = {}
                    client_updated_at = datetime.fromisoformat(change.get("updated_at", ""))

                    # Se cliente é mais recente ou escolheu client_wins
                    if (strategy == ConflictResolutionStrategy.CLIENT_WINS or
                            (strategy == ConflictResolutionStrategy.LATEST_WINS and
                             client_updated_at > server_user.updated_at)):

                        # Aplicar mudanças do cliente
                        if "email" in change:
                            update_data["email"] = change["email"]
                        if "is_active" in change:
                            update_data["is_active"] = change["is_active"]

                        if update_data:
                            updated_user = await user_repository.update_with_password(
                                db,
                                db_obj=server_user,
                                obj_in=update_data
                            )

                            results.append({
                                "id": str(updated_user.id),
                                "status": "updated",
                                "conflicts_resolved": len(update_data)
                            })
                        else:
                            results.append({
                                "id": str(server_user.id),
                                "status": "no_changes"
                            })
                else:
                    # Não existe - item deletado ou não encontrado
                    conflicts.append({
                        "error": "User not found",
                        "id": user_id
                    })

            return {
                "sync_timestamp": DateTimeUtil.format_iso(DateTimeUtil.utcnow()),
                "results": results,
                "conflicts": conflicts,
                "sync_status": "complete"
            }

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported entity type: {entity_type}"
            )

    except Exception as e:
        logger.exception(f"Error during client sync of {entity_type}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error synchronizing client changes: {str(e)}"
        )
