# app/adapters/outbound/persistence/models/user_group/base_model.py

"""
Base class for SQLAlchemy models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos."""


def register_password_protection():
    """
    Registra o PasswordProtectionMiddleware em todos os modelos que tenham o campo `password`.
    """
    from sqlalchemy import event
    from app.shared.middleware.logging_middleware import PasswordProtectionMiddleware

    for mapper in Base.registry.mappers:
        model = mapper.class_
        if hasattr(model, 'password'):
            event.listen(model, 'before_insert', PasswordProtectionMiddleware.before_insert_or_update)
            event.listen(model, 'before_update', PasswordProtectionMiddleware.before_insert_or_update)


def register_all_events():
    """
    Registra todos os eventos para os modelos.
    """
    register_password_protection()

    # Registra eventos de timezone
    from app.adapters.outbound.persistence.events import register_datetime_events
    register_datetime_events()
