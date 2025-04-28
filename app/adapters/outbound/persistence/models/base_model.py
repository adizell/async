# app/adapters/outbound/persistence/models/base_model.py

from sqlalchemy import event
from sqlalchemy.orm import declarative_base
from app.shared.middleware.logging_middleware import PasswordProtectionMiddleware

Base = declarative_base()


# Registrar middleware em todos os modelos que herdam de Base
@event.listens_for(Base, 'before_insert', propagate=True)
def protect_password_on_insert(mapper, connection, target):
    if hasattr(target, 'password'):
        PasswordProtectionMiddleware.before_insert_or_update(mapper, connection, target)


@event.listens_for(Base, 'before_update', propagate=True)
def protect_password_on_update(mapper, connection, target):
    if hasattr(target, 'password'):
        PasswordProtectionMiddleware.before_insert_or_update(mapper, connection, target)
