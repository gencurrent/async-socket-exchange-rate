"""
Test RPC models
"""

import pytest
from pydantic import ValidationError

from rpc.models import RPCCommandModel


@pytest.mark.asyncio
async def test_rpc_message_model():
    """
    Test RPCMessage model
    """
    # Valid RPC message
    RPCCommandModel(action="assets", message={}, message2={})  # type: ignore

    # `message` is of invalid type
    with pytest.raises(ValidationError) as exception:
        RPCCommandModel(action="assets", message="", message2="")  # type: ignore

    original_exception = exception.value
    errors = original_exception.errors()
    error = errors[0]
    assert error["loc"][0] == "message"
    assert error["msg"] == "Input should be a valid dictionary"

    # `message` is not supplied
    with pytest.raises(ValidationError) as exception:
        RPCCommandModel(action="assets")  # type: ignore

    original_exception = exception.value
    errors = original_exception.errors()
    error = errors[0]
    assert error["loc"][0] == "message"
    assert error["msg"] == "Field required"
