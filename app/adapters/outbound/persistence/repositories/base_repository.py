# app/adapters/outbound/persistence/repositories/base_repository.py (async version)

"""
Async Base Repository

Provides a robust, scalable, and clean implementation of generic CRUD operations
for SQLAlchemy models in asynchronous applications.

Handles:
- Get single or multiple records
- Create, update, delete records
- Existence checks
- Count records with filters

Implements uniform logging and error handling for database operations.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.future import select
import logging

from app.adapters.outbound.persistence.models.user_group.base_model import Base
from app.domain.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    DatabaseOperationException,
)

# Define generic type for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)
# Define generic types for Pydantic DTOs
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

# Configure logger
logger = logging.getLogger(__name__)


class AsyncCRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic asynchronous CRUD base class.
    """

    def __init__(self, model: Type[ModelType]):
        """
        Initialize the repository with an SQLAlchemy model.

        Args:
            model: SQLAlchemy model class associated with this repository
        """
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{model.__name__}")

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Retrieve an object by ID."""
        try:
            query = select(self.model).where(self.model.id == id)
            result = await db.execute(query)
            return result.unique().scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Error fetching {self.model.__name__} with ID {id}: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error fetching {self.model.__name__}", original_error=e
            )

    async def get_by_field(self, db: AsyncSession, field_name: str, value: Any) -> Optional[ModelType]:
        """Retrieve an object by a specific field."""
        try:
            query = select(self.model).where(getattr(self.model, field_name) == value)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(f"Error fetching {self.model.__name__} by {field_name}={value}: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error fetching {self.model.__name__} by {field_name}", original_error=e
            )

    async def exists(self, db: AsyncSession, **filters) -> bool:
        """Check if a record exists matching the given filters."""
        try:
            query = select(self.model)
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

            result = await db.execute(query.limit(1))
            return result.scalars().first() is not None
        except SQLAlchemyError as e:
            self.logger.error(f"Error checking existence of {self.model.__name__}: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error checking existence of {self.model.__name__}", original_error=e
            )

    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100, **filters) -> List[ModelType]:
        """Retrieve multiple records with optional filters."""
        try:
            query = select(self.model)

            # Apply dynamic filters
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    if isinstance(value, str) and value.startswith("%") and value.endswith("%"):
                        # LIKE filter for strings with wildcards
                        query = query.where(getattr(self.model, field).ilike(value))
                    else:
                        # Standard equality filter
                        query = query.where(getattr(self.model, field) == value)

            result = await db.execute(query.offset(skip).limit(limit))
            return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(f"Error listing {self.model.__name__}s: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error listing {self.model.__name__}s", original_error=e
            )

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        try:
            # Convert Pydantic schema to dictionary
            obj_in_data = jsonable_encoder(obj_in)

            # Create model instance with data
            db_obj = self.model(**obj_in_data)

            # Add and persist in database
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)

            self.logger.info(f"{self.model.__name__} created with ID: {db_obj.id}")
            return db_obj

        except IntegrityError as e:
            await db.rollback()
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg:
                self.logger.warning(f"Attempt to create duplicate {self.model.__name__}: {str(e)}")
                raise ResourceAlreadyExistsException(
                    detail=f"{self.model.__name__} with these data already exists"
                )
            self.logger.error(f"Integrity error creating {self.model.__name__}: {str(e)}")
            raise DatabaseOperationException(original_error=e)

        except SQLAlchemyError as e:
            await db.rollback()
            self.logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error creating {self.model.__name__}", original_error=e
            )

    async def update(self, db: AsyncSession, *, db_obj: ModelType,
                     obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        Update an existing record.

        Args:
            db: Async database session
            db_obj: Existing database object to update
            obj_in: New data to apply (schema or dict)

        Returns:
            Updated model instance

        Raises:
            ResourceAlreadyExistsException: If update violates unique constraints
            DatabaseOperationException: For other database errors
        """
        try:
            # Convert input data to dictionary if it's a schema
            update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)

            # Apply updates to existing object
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Save changes to database
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)

            self.logger.info(f"{self.model.__name__} with ID {db_obj.id} updated")
            return db_obj

        except IntegrityError as e:
            await db.rollback()
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg:
                self.logger.warning(f"Uniqueness violation updating {self.model.__name__}: {str(e)}")
                raise ResourceAlreadyExistsException(
                    detail=f"Could not update {self.model.__name__}: value already exists"
                )
            self.logger.error(f"Integrity error updating {self.model.__name__}: {str(e)}")
            raise DatabaseOperationException(original_error=e)

        except SQLAlchemyError as e:
            await db.rollback()
            self.logger.error(f"Error updating {self.model.__name__}: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error updating {self.model.__name__}", original_error=e
            )

    async def remove(self, db: AsyncSession, *, id: Any) -> ModelType:
        """Remove a record by ID."""
        try:
            # Find the entity
            obj = await self.get(db, id)
            if not obj:
                raise ResourceNotFoundException(
                    message=f"{self.model.__name__} with ID {id} not found", resource_id=id
                )

            # Remove the entity
            await db.delete(obj)
            await db.commit()

            self.logger.info(f"{self.model.__name__} with ID {id} removed")
            return obj

        except IntegrityError as e:
            await db.rollback()
            self.logger.error(f"Integrity error removing {self.model.__name__}: {str(e)}")
            raise DatabaseOperationException(
                message=f"Cannot remove {self.model.__name__} as it is linked to other resources",
                original_error=e
            )

        except ResourceNotFoundException:
            # Pass through the already formatted exception
            await db.rollback()
            raise

        except SQLAlchemyError as e:
            await db.rollback()
            self.logger.error(f"Error removing {self.model.__name__}: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error removing {self.model.__name__}", original_error=e
            )

    async def count(self, db: AsyncSession, **filters) -> int:
        """Count records matching filters."""
        try:
            query = select(func.count()).select_from(self.model)
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

            result = await db.execute(query)
            return result.scalar_one()
        except SQLAlchemyError as e:
            self.logger.error(f"Error counting {self.model.__name__}s: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error counting {self.model.__name__}s", original_error=e
            )
