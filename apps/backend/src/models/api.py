"""API models for request and response data."""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CommandRequest(BaseModel):
    """Command request model for API endpoints."""
    
    command_type: str = Field(..., description="The type of command to execute")
    payload: Optional[Dict[str, Any]] = Field(None, description="Command parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "command_type": "RequestConceptGeneration",
                "payload": {
                    "theme_preferences": ["科幻", "悬疑"],
                    "style_preferences": ["快节奏", "第一人称"]
                }
            }
        }


class CommandResponse(BaseModel):
    """Command response model for API endpoints."""
    
    command_id: UUID = Field(..., description="The ID of the created command")
    status: str = Field(..., description="The status of the command")
    message: str = Field(..., description="A human-readable message about the command")
    
    class Config:
        json_schema_extra = {
            "example": {
                "command_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "RECEIVED",
                "message": "Command received and will be processed"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model for API endpoints."""
    
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    duplicate_command_id: Optional[UUID] = Field(None, description="ID of the duplicate command if applicable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "DUPLICATE_COMMAND",
                "message": "Command already processing",
                "duplicate_command_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class CommandResult(BaseModel):
    """Internal command processing result."""
    
    command_id: UUID = Field(..., description="The ID of the processed command")
    status: str = Field(..., description="The status of the command processing")
    message: str = Field(..., description="A message about the processing result")
    
    class Config:
        json_schema_extra = {
            "example": {
                "command_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "COMPLETED",
                "message": "Command processed successfully"
            }
        }