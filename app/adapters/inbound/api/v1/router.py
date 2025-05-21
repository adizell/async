# app/adapters/inbound/api/v1/router.py

from fastapi import APIRouter
# Manter em ordem alfabética
from app.adapters.inbound.api.v1.endpoints import (
    auth_endpoint,
    auth_content_type_endpoint,
    auth_cookie_endpoint,
    auth_group_permissions_endpoint,
    auth_permission_endpoint,
    client_endpoint,
    auth_group_endpoint,
    sync_endpoint,
    user_access_groups_endpoint,
    user_endpoint
)

api_router = APIRouter()

# Incluir router de autenticação baseada em cookies
api_router.include_router(auth_cookie_endpoint.router)

# Incluir os routers dos endpoints
api_router.include_router(auth_endpoint.router)
api_router.include_router(user_endpoint.router)

# Incluir routers de permission, groups e content types
api_router.include_router(auth_content_type_endpoint.router)
api_router.include_router(auth_permission_endpoint.router)
api_router.include_router(auth_group_endpoint.router)
api_router.include_router(auth_group_permissions_endpoint.router)
api_router.include_router(user_access_groups_endpoint.router)

# Incluir router de sincronização
api_router.include_router(sync_endpoint.router)

# Incluir routers dos clients (JWT e URL)
api_router.include_router(client_endpoint.jwt_router)
api_router.include_router(client_endpoint.create_url_router)
api_router.include_router(client_endpoint.update_url_router)
