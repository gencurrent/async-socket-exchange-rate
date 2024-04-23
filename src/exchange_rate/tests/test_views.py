"""
Test views
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import WebSocket
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_socket__invalid_input(test_client: TestClient) -> None:
    """
    Test the websocket: the input is completely invalid
    """
    with test_client.websocket_connect("/") as ws:
        ws.send_json({})
        response = ws.receive_json()

    assert isinstance(response, dict)
    errors = response["errors"]
    # 1st error
    msg = errors[0]
    assert msg["loc"] == "action"
    assert msg["msg"] == "Field required"
    assert msg["input"] == {}

    # 2nd error
    msg = errors[1]
    assert msg["loc"] == "message"
    assert msg["msg"] == "Field required"
    assert msg["input"] == {}


@pytest.mark.asyncio
async def test_socket__unknown_action(test_client: TestClient) -> None:
    """
    Test the websocket: the action is unknown returning an error response message
    """
    with test_client.websocket_connect("/") as ws:
        ws.send_json({"action": "unknown", "message": {}})
        response = ws.receive_json()

    message = response["message"]

    assert message == {"errors": [{"msg": "Unknown action"}]}

@pytest.mark.skip(
    reason="Async websockets are not supported yet in FastAPI. "
    "The potential workaround solutions require additional research"
)
@pytest.mark.asyncio
async def test_socket__assets(assets, test_client: TestClient) -> None:
    """
    Test the websocket: "assets" action to list the available assets
    """
    with test_client.websocket_connect("/") as ws:
        ws.send_json({"action": "assets", "message": {}})
        response = ws.receive_json()

    errors = response["errors"]
    msg = errors[0]
    assert msg["loc"] == "action"
    assert (
        msg["msg"]
        == "Value error, the action is not supported. The supported actions are ('assets', 'subscribe')"
    )
    assert msg["input"] == "unknown"
