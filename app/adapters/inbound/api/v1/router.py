# app/adapters/inbound/api/v1/router.py

from fastapi import APIRouter
from app.adapters.inbound.api.v1.endpoints import client_auth, user_auth, auth

api_router = APIRouter()

# Include the routers for endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(user_auth.router, prefix="/user", tags=["User"])

# Include client routers
api_router.include_router(client_auth.jwt_router)
api_router.include_router(client_auth.create_url_router)
api_router.include_router(client_auth.update_url_router)
