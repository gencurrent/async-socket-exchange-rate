"""
Test RPC models
"""

import pytest

from rpc.models import RPCMessageModel

from pydantic import ValidationError

@pytest.mark.asyncio
async def test_rpc_message_model():
    """
    Test RPCMessage model
    """
    # Valid RPC message
    RPCMessageModel(action="assets", message={}, message2={})

    # `message` is of invalid type
    with pytest.raises(ValidationError) as exception:
        RPCMessageModel(action="assets", message="", message2="")

    errors = exception.value.errors()
    error = errors[0]
    assert error["loc"][0] == "message"
    assert error["msg"] == "Input should be a valid dictionary"

    # `message` is not supplied
    with pytest.raises(ValidationError) as exception:
        RPCMessageModel(action="assets")

    errors = exception.value.errors()
    error = errors[0]
    assert error["loc"][0] == "message"
    assert error["msg"] == "Field required"