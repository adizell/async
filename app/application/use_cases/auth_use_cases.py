# app/application/use_cases/auth_use_cases.py

from datetime import datetime, timedelta
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.domain.exceptions import ResourceNotFoundException, InvalidCredentialsException
from app.application.dtos.user_dto import UserCreate, TokenData
from app.adapters.outbound.persistence.models import User, RefreshToken
from app.adapters.outbound.security.auth_user_manager import UserAuthManager

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations"""

    def __init__(self, db_session: AsyncSession):
        """Initialize with database session"""
        self.db = db_session

    async def register_user(self, user_input: UserCreate) -> User:
        """Register a new user"""
        try:
            # Check if user exists
            existing_user = await self.db.query(User).filter(User.email == user_input.email).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )

            # Create user
            hashed_password = UserAuthManager.hash_password(user_input.password)
            new_user = User(
                email=user_input.email,
                password=hashed_password,
                is_superuser=False
            )

            # Add user to default group
            user_group = await self.db.query(AuthGroup).filter(AuthGroup.name == "user").first()
            if user_group:
                new_user.groups.append(user_group)

            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)

            return new_user

        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error registering user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )

    async def login_user(self, user_input: UserCreate) -> TokenData:
        """Authenticate user and generate tokens"""
        try:
            # Verify credentials
            user = await self.db.query(User).filter(User.email == user_input.email).first()

            if not user:
                raise InvalidCredentialsException(detail="Invalid email or password")

            if not user.is_active:
                raise ResourceInactiveException(detail="User account is inactive")

            if not UserAuthManager.verify_password(user_input.password, user.password):
                raise InvalidCredentialsException(detail="Invalid email or password")

            # Generate tokens
            access_token_expires = timedelta(minutes=120)
            access_token = UserAuthManager.create_access_token(
                subject=str(user.id),
                expires_delta=access_token_expires
            )

            # Create refresh token with longer expiration (7 days)
            refresh_token_expires = datetime.utcnow() + timedelta(days=7)
            refresh_token_value = UserAuthManager.create_refresh_token(subject=str(user.id))

            # Store refresh token in database
            db_refresh_token = RefreshToken(
                token=refresh_token_value,
                user_id=user.id,
                expires_at=refresh_token_expires
            )

            self.db.add(db_refresh_token)
            await self.db.commit()

            # Return both tokens
            return TokenData(
                access_token=access_token,
                refresh_token=refresh_token_value,
                expires_at=datetime.utcnow() + access_token_expires
            )

        except (InvalidCredentialsException, ResourceInactiveException) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error during login: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )

    async def refresh_token(self, refresh_token: str) -> TokenData:
        """Generate new access token using a refresh token"""
        try:
            # Verify the refresh token exists and is valid
            token_record = await self.db.query(RefreshToken).filter(
                RefreshToken.token == refresh_token,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.utcnow()
            ).first()

            if not token_record:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token"
                )

            # Get the user
            user = await self.db.query(User).filter(User.id == token_record.user_id).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is inactive or not found"
                )

            # Generate new access token
            access_token_expires = timedelta(minutes=120)
            access_token = UserAuthManager.create_access_token(
                subject=str(user.id),
                expires_delta=access_token_expires
            )

            # Return the new access token
            return TokenData(
                access_token=access_token,
                refresh_token=refresh_token,  # Return the same refresh token
                expires_at=datetime.utcnow() + access_token_expires
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error refreshing token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )
