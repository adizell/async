# app/adapters/inbound/api/v1/endpoints/__init__.py

from .client_auth import jwt_router, create_url_router, update_url_router
from .user import router as user_auth
from .auth import router as auth
