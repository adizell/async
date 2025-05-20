# app/application/dtos/user_dto.py

"""
Schemas for user data.

This module defines DTOs (Data Transfer Objects) for validating and
serializing data related to users, including registration, login,
profile management and authentication.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.application.dtos.base_dto import CustomBaseModel
from app.shared.utils.input_validation import InputValidator
from pydantic import (
    field_validator,
    EmailStr,
    constr,
    Field,
)

# Import GroupOutput and PermissionOutput from group_dto.py instead of redefining
from app.application.dtos.group_dto import GroupOutput, PermissionOutput


class UserBase(CustomBaseModel):
    """
    Schema base for user data.

    Contains the attributes common to all user DTOs.
    """
    email: EmailStr = Field(
        ...,
        description="Email of the user. Must be a valid and unique email.",
    )

    @field_validator('email')
    def validate_email_security(cls, v):
        """
        Validates the security of the email to prevent injections.

        Args:
            v: Email to validate

        Returns:
            Validated email

        Raises:
            ValueError: If the email is invalid
        """
        is_valid, error_msg = InputValidator.validate_email(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class UserLogin(CustomBaseModel):
    """
    Schema for user login.

    Used for user authentication via email and password.
    """

    email: EmailStr = Field(
        ...,
        description="Email of the user. Must be a valid and registered email.",
    )
    password: str = Field(
        ...,
        description="User's password used for authentication."
    )


class UserCreate(UserBase):
    """
    Schema for creating a new user.

    Extends UserBase and adds the password.
    """
    password: constr(min_length=6) = Field(
        ..., description="User's password, with a minimum of 6 characters."
    )

    @field_validator('password')
    def validate_password_security(cls, v):
        """
        Validates the password to ensure minimum security requirements.

        Args:
            v: Password to validate

        Returns:
            Validated password

        Raises:
            ValueError: If the password doesn't meet requirements
        """
        is_valid, error_msg = InputValidator.validate_password(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class UserOutput(UserBase):
    """
    Schema for returning user data.

    Used to return user data in APIs without exposing sensitive data.
    """
    id: UUID = Field(..., description="User's unique identifier.")
    is_active: bool = Field(..., description="Indicates if the user is active.")
    created_at: datetime = Field(..., description="User creation date and time.")
    is_superuser: bool = Field(..., description="Indicates if the user is a superuser.")
    updated_at: Optional[datetime] = Field(None, description="Date and time of the last update.")

    class Config:
        from_attributes = True

    @classmethod
    def from_domain(cls, domain_user: 'DomainUser') -> 'UserOutput':
        """
        Cria um DTO a partir do modelo de domínio.

        Args:
            domain_user: Modelo de domínio User

        Returns:
            UserOutput: DTO para saída de dados do usuário
        """
        return cls(
            id=domain_user.id,
            email=domain_user.email,
            is_active=domain_user.is_active,
            is_superuser=domain_user.is_superuser,
            created_at=domain_user.created_at,
            updated_at=domain_user.updated_at
        )


class UserGroupsOutput(CustomBaseModel):
    """Schema for user with groups output."""
    id: UUID = Field(..., description="ID of the user")
    email: str = Field(..., description="Email of the user")
    is_active: bool = Field(..., description="Indicates if the user is active")
    is_superuser: bool = Field(..., description="Indicates if the user is a superuser")
    groups: List[GroupOutput] = Field(default_factory=list, description="Groups assigned to the user")

    class Config:
        from_attributes = True


class UserSelfUpdate(CustomBaseModel):
    """
    Schema for users to update their own data.

    Only allows updating email and password.
    """
    email: Optional[EmailStr] = Field(
        None,
        description="Email of the user. Must be a valid and unique email.",
    )
    password: Optional[constr(min_length=6)] = Field(
        None, description="New password for the user, with a minimum of 6 characters."
    )
    current_password: Optional[str] = Field(
        None, description="Current password (required to confirm changes)."
    )


class UserUpdate(CustomBaseModel):
    """
    Schema for administrators to update any user.

    Allows updating email, password, active status and superuser status.
    """
    email: Optional[EmailStr] = Field(
        None,
        description="Email of the user. Must be a valid and unique email.",
    )
    password: Optional[constr(min_length=6)] = Field(
        None, description="New password for the user, with a minimum of 6 characters."
    )
    is_active: Optional[bool] = Field(
        None, description="Defines if the user is active or inactive."
    )
    is_superuser: Optional[bool] = Field(
        None, description="Defines if the user is a superuser."
    )


class UserListOutput(CustomBaseModel):
    """
    Schema for listing users.

    Used in user listing APIs.
    """
    id: UUID
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserWithPermissionsOutput(UserOutput):
    """Schema for user with groups and permissions."""
    groups: List[GroupOutput] = Field(default_factory=list, description="User's groups")
    permissions: List[PermissionOutput] = Field(default_factory=list, description="User's direct permissions")

    class Config:
        from_attributes = True


class UserPermissionOutput(CustomBaseModel):
    """Schema for detailed user permissions output."""
    user_id: str = Field(..., description="ID of the user")
    email: str = Field(..., description="Email of the user")
    groups: List[GroupOutput] = Field(default_factory=list, description="Groups assigned to the user")
    direct_permissions: List[PermissionOutput] = Field(default_factory=list,
                                                       description="Permissions directly assigned to the user")
    effective_permissions: List[str] = Field(default_factory=list, description="All effective permission codenames")

    class Config:
        from_attributes = True


########################################################################
# For backward compatibility with code that used `User`
########################################################################
User = UserCreate


########################################################################
# Authentication token classes
########################################################################
class TokenData(CustomBaseModel):
    """
    Schema for authentication token data.

    Used to return JWT token and expiration information.
    """
    access_token: str = Field(..., description="JWT access token.")
    refresh_token: str = Field(..., description="Refresh token for obtaining new access tokens.")
    expires_at: datetime = Field(..., description="Token expiration date and time.")

    class Config:
        from_attributes = True


class RefreshTokenRequest(CustomBaseModel):
    """
    Schema for refresh token request.
    """
    refresh_token: str = Field(..., description="Refresh token for obtaining a new access token.")
