# app/application/dtos/group_dto.py

"""
Schemas for group and permission management.

This module defines DTOs (Data Transfer Objects) for validating and
serializing data related to groups and permissions.
"""

from typing import List, Optional
from pydantic import Field
from app.application.dtos.base_dto import CustomBaseModel


class GroupBase(CustomBaseModel):
    """Base schema for group data."""
    name: str = Field(..., description="Name of the group")


class GroupCreate(GroupBase):
    """Schema for creating a new group."""
    pass


class GroupUpdate(GroupBase):
    """Schema for updating an existing group."""
    name: Optional[str] = Field(None, description="Updated name of the group")


class PermissionOutput(CustomBaseModel):
    """Schema for permission output."""
    id: int = Field(..., description="ID of the permission")
    name: str = Field(..., description="Name of the permission")
    codename: str = Field(..., description="Codename of the permission")
    content_type_id: int = Field(..., description="ID of the content type")

    class Config:
        from_attributes = True


class GroupPermissionUpdate(CustomBaseModel):
    """Schema for adding or removing permissions from a group."""
    permission_ids: List[int] = Field(..., description="List of permission IDs to add/remove")


class GroupOutput(GroupBase):
    """Schema for group output including its permissions."""
    id: int = Field(..., description="ID of the group")
    permissions: List[PermissionOutput] = Field(default_factory=list, description="Permissions assigned to the group")

    class Config:
        from_attributes = True


class ContentTypeOutput(CustomBaseModel):
    """Schema for content type output."""
    id: int = Field(..., description="ID of the content type")
    app_label: str = Field(..., description="Application label")
    model: str = Field(..., description="Model name")

    class Config:
        from_attributes = True


class UserGroupUpdate(CustomBaseModel):
    """Schema for adding or removing groups from a user."""
    group_ids: List[int] = Field(..., description="List of group IDs to add/remove")


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
