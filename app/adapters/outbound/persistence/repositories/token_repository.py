# app/adapters/outbound/persistence/repositories/token_repository.py (async version)

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.outbound.persistence.models.user_group.token_blacklist_model import TokenBlacklist
from app.domain.exceptions import DatabaseOperationException


class AsyncTokenRepository:
    """Repository for managing token blacklist."""

    @staticmethod
    async def add_to_blacklist(db: AsyncSession, jti: str, expires_at: datetime,
                               revoked_at: datetime) -> TokenBlacklist:
        """
        Add a token to the blacklist.

        Args:
            db: Async database session
            jti: JWT ID to blacklist
            expires_at: When the token naturally expires
            revoked_at: When the token was manually revoked

        Returns:
            The created TokenBlacklist record
        """
        try:
            token = TokenBlacklist(
                jti=jti,
                expires_at=expires_at,
                revoked_at=revoked_at,
            )
            db.add(token)
            await db.commit()
            await db.refresh(token)
            return token
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseOperationException(
                message="Error adding token to blacklist",
                original_error=e
            )

    @staticmethod
    async def is_blacklisted(db: AsyncSession, jti: str) -> bool:
        """
        Check if a token is in the blacklist.

        Args:
            db: Async database session
            jti: JWT ID to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            query = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
            result = await db.execute(query)
            token = result.scalar_one_or_none()
            return token is not None
        except SQLAlchemyError as e:
            raise DatabaseOperationException(
                message="Error checking token blacklist",
                original_error=e
            )

    @staticmethod
    async def cleanup_expired(db: AsyncSession) -> int:
        """
        Remove expired tokens from blacklist to keep the table size manageable.

        Args:
            db: Async database session

        Returns:
            Number of records deleted
        """
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            query = select(TokenBlacklist).where(TokenBlacklist.expires_at < now)
            result = await db.execute(query)
            expired_tokens = result.scalars().all()

            count = 0
            for token in expired_tokens:
                await db.delete(token)
                count += 1

            await db.commit()
            return count
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseOperationException(
                message="Error cleaning up expired blacklisted tokens",
                original_error=e
            )


# Create singleton instance
token_repository = AsyncTokenRepository()
