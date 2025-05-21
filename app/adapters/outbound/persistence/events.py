# app/adapters/outbound/persistence/events.py

"""
Event listeners for SQLAlchemy ORM lifecycle.

This module adds event listeners to handle timezone-aware
datetime fields during creation and updates of entities.
"""

import logging
from sqlalchemy import event
from datetime import datetime
from sqlalchemy.orm import Mapper

from app.shared.utils.datetime_utils import DateTimeUtil

logger = logging.getLogger(__name__)


def register_datetime_events():
    """
    Register event listeners for datetime fields in SQLAlchemy models.
    """
    from app.adapters.outbound.persistence.models.user_group.base_model import Base

    @event.listens_for(Base, 'before_insert', propagate=True)
    def set_created_at(mapper, connection, target):
        """
        Set created_at and updated_at to current local time before insert.
        """
        if hasattr(target, 'created_at') and (target.created_at is None):
            target.created_at = DateTimeUtil.for_storage()

        if hasattr(target, 'updated_at'):
            target.updated_at = DateTimeUtil.for_storage()

    @event.listens_for(Base, 'before_update', propagate=True)
    def set_updated_at(mapper, connection, target):
        """
        Set updated_at to current local time before update.
        """
        if hasattr(target, 'updated_at'):
            target.updated_at = DateTimeUtil.for_storage()

    logger.info("DateTime event listeners registered for SQLAlchemy models")
