"""
Test views
"""

import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient
from httpx import AsyncClient

from db.models.exchange_rate import Asset


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


@pytest.mark.asyncio
async def test_socket__assets(assets, test_client: TestClient) -> None:
    """
    Test the websocket: "assets" action to list the available assets
    """

    with test_client.websocket_connect("/") as ws:
        ws.send_json({"action": "assets", "message": {}})
        response = ws.receive_json()

    assert "action" in response
    assert response["action"] == "assets"

    assert "message" in response
    message = response["message"]
    assert "assets" in message
    assets = message["assets"]
    db_assets = await Asset.find_assets_from_settings().to_list()
    assert assets == [db_asset.model_dump() for db_asset in db_assets]
