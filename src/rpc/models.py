"""
General RPC models
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator

from db.models import ExchangeRate


class RPCMessageModel(BaseModel):
    """General RPC call (input / output) messsage format model"""

    action: str = Field(description="Action name")
    message: Dict[str, Any] = Field(description="The message content", )


class RPCErrorMessageModel(BaseModel):
    """RPC error nested inside the `message` field"""

    errors: List[Dict[str, Any]] = Field(description="List of errors")