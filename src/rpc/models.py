"""
General RPC models
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError, field_validator

from db.models import ExchangeRate


class RPCMessageModel(BaseModel):
    """General RPC call (input / output) messsage format model"""

    action: str = Field(description="Action name")
    message: Dict[str, Any] = Field(
        description="The message content",
    )


class RPCErrorMessageModel(BaseModel):
    """RPC error nested inside the `message` field"""

    errors: List[Dict[str, Any]] = Field(description="List of errors")

    @staticmethod
    def from_validation_error(exception: ValidationError) -> "RPCErrorMessageModel":
        """
        Create an RPCErrorMessageModel instance from the ValidationError exception
        """
        errors = exception.errors()
        result_errors = []
        for error in errors:
            error_loc = error["loc"]
            loc = (len(error_loc) == 1 and error_loc[0]) or error_loc
            result_errors.append(
                {
                    "loc": loc,
                    "msg": error["msg"],
                    "input": error["input"],
                }
            )
        return RPCErrorMessageModel(errors=result_errors)
