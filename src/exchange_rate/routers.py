"""
Exchange rate application router
"""

import asyncio
from json.decoder import JSONDecodeError
from typing import Any, Coroutine, Dict, List, Tuple


from loguru import logger as _LOG
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from db.models import Asset
from exchange_rate.client_service import (
    AbstractExchangeRateClientService,
    ExchangeRateClientService,
)
from exchange_rate.models import RPCSubscribeMessageModel
from exchange_rate.utils import single_error_rpc_response
from rpc.models import RPCMessageModel, RPCErrorMessageModel


ASSET_ID_FIELD = "assetId"

router = APIRouter()


class WebSocketConnectionManager:
    """The connection manager to handle websocket connections"""

    CLIENT_SERVICE = "client_service"
    LATEST_ACTION = "latest_action"

    def __init__(self) -> None:
        """Initialize"""
        self._connections: List[WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Initialize the connection with the client"""
        await websocket.accept()
        client_service: AbstractExchangeRateClientService = ExchangeRateClientService()
        initial_state = {
            self.CLIENT_SERVICE: client_service,
            self.LATEST_ACTION: None,  # str
        }
        self._connections[websocket] = initial_state

    def disconnect(self, websocket: WebSocket) -> None:
        """Handle the client disconnection"""
        del self._connections[websocket]

    def get_client_service(
        self, websocket: WebSocket
    ) -> AbstractExchangeRateClientService:
        """Get the related ExchangeRateClientService"""
        service = self._connections[websocket][self.CLIENT_SERVICE]
        return service

    def get_latest_action(self, websocket: WebSocket) -> str:
        """Get the related ExchangeRateClientService"""
        action: str = self._connections[websocket][self.LATEST_ACTION]
        return action

    async def receive_command(self, websocket: WebSocket) -> RPCMessageModel | None:
        """Read the incoming JSON RPC command"""
        try:
            json_command = await websocket.receive_json()
        except JSONDecodeError:
            await CONNECTION_MANAGER.send_message(
                websocket, "Could not parse the JSON command"
            )
            return None
        if not isinstance(json_command, dict):
            await CONNECTION_MANAGER.send_message(
                websocket,
                f"Invalid type of the message: {type(json_command)}."
                ""
                """ Command must be a valid JSON mapping""",
            )
            return None
        try:
            rpc_message = RPCMessageModel(**json_command)
            self._connections[websocket][self.LATEST_ACTION] = rpc_message.action
            return rpc_message
        except ValidationError as exception:
            error_message = RPCErrorMessageModel.from_validation_error(exception)
            await CONNECTION_MANAGER.send_message(websocket, error_message)
            return None

    async def send_message(
        self,
        websocket: WebSocket,
        message: str | Dict[Any, Any] | List[Any] | BaseModel,
    ) -> None:
        """Send message"""
        _LOG.info(
            f'Meesage to send is "{message}"',
        )

        if isinstance(message, str):
            await websocket.send_text(message)
        elif isinstance(message, BaseModel):
            await websocket.send_json(message.model_dump())
        elif isinstance(message, (dict, list)):
            try:
                await websocket.send_json(message)
            except TypeError:
                return
        else:
            raise TypeError("Unsupported message type")


CONNECTION_MANAGER = WebSocketConnectionManager()


@router.websocket("/")
async def exchange_rate(websocket: WebSocket):
    """
    Subscribe to relevant, up-to-date exchange rates
    """
    await CONNECTION_MANAGER.connect(websocket)
    client_service: AbstractExchangeRateClientService = (
        CONNECTION_MANAGER.get_client_service(websocket)
    )
    try:
        while True:

            rpc_message: RPCMessageModel | None = (
                await CONNECTION_MANAGER.receive_command(websocket)
            )
            if not rpc_message:
                continue

            match (rpc_message.action):
                case "assets":
                    async for message in client_service.rpc_assets():
                        await CONNECTION_MANAGER.send_message(websocket, message)
                case "subscribe":
                    await handle_subscribe_action(websocket, rpc_message)
                case _:
                    error_message = single_error_rpc_response(
                        rpc_message.action, "Unknown action"
                    )
                    await CONNECTION_MANAGER.send_message(websocket, error_message)
    except WebSocketDisconnect:
        CONNECTION_MANAGER.disconnect(websocket)


async def handle_subscribe_action(
    websocket: WebSocket, rpc_message: RPCMessageModel
) -> Coroutine[Any, Any, None]:

    try:
        rpc_subscribe_message_model = RPCSubscribeMessageModel(**rpc_message.message)
    except ValidationError as exception:
        error_message = RPCErrorMessageModel.from_validation_error(exception)
        await CONNECTION_MANAGER.send_message(websocket, error_message)
        return

    # Subscribe
    client_service: AbstractExchangeRateClientService = (
        CONNECTION_MANAGER.get_client_service(websocket)
    )
    error_message = await client_service.rpc_switch_asset_id(
        rpc_subscribe_message_model.asset_id
    )
    if error_message:
        await CONNECTION_MANAGER.send_message(websocket, error_message)
        return

    async def yield_exchange_rate_messages():
        async for message in client_service.rpc_subscribe():
            await CONNECTION_MANAGER.send_message(websocket, message)

    async def listen_to_asset_switch():
        while True:
            rpc_message = await CONNECTION_MANAGER.receive_command(websocket)
            if not rpc_message:
                continue
            asset_id = rpc_message.message.pop(ASSET_ID_FIELD, None)
            if not (rpc_message.action == "subscribe" and isinstance(asset_id, int)):
                response = single_error_rpc_response(
                    rpc_message.action, f"`{ASSET_ID_FIELD}` must be integer"
                )
                await CONNECTION_MANAGER.send_message(websocket, response)
                continue

            error_message = await client_service.rpc_switch_asset_id(asset_id)
            if error_message:
                await CONNECTION_MANAGER.send_message(websocket, error_message)
                continue

    await asyncio.gather(
        yield_exchange_rate_messages(),
        listen_to_asset_switch(),
    )
