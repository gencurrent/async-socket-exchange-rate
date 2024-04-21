"""
The main file yielding the application instance
"""

import asyncio
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Tuple
from contextlib import asynccontextmanager

from loguru import logger
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from db.database import initialize_database
from db.models import Asset
from exchange_rate.client_service import ExchangeRateClientService
from rpc.models import RPCMessageModel


_LOG = logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Server lifespan pre- and post- processing function
    """
    _LOG.info("On server initalization")
    await initialize_database()
    yield
    _LOG.info("On server teardown")


app = FastAPI(lifespan=lifespan)


class WebSocketConnectionManager:
    """The connection manager to handle websocket connections"""

    CLIENT_SERVICE = "client_service"

    def __init__(self) -> None:
        """Initialize"""
        self._connections: List[WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Initialize the connection with the client"""
        await websocket.accept()
        initial_state = {}
        client_service = ExchangeRateClientService()
        initial_state[self.CLIENT_SERVICE] = client_service
        self._connections[websocket] = initial_state

    def disconnect(self, websocket: WebSocket) -> None:
        """Handle the client disconnection"""
        del self._connections[websocket]

    def get_exchange_rate_client_service(
        self, websocket: WebSocket
    ) -> ExchangeRateClientService:
        """Get the related ExchangeRateClientService"""
        service = self._connections[websocket][self.CLIENT_SERVICE]
        return service

    async def receive_command(self, websocket: WebSocket) -> RPCMessageModel | None:
        """Read the incoming JSON RPC command"""
        try:
            json_command = await websocket.receive_json()
        except JSONDecodeError:
            await CONNECTIONS_MANAGER.send_message(
                websocket, "Could not parse the JSON command"
            )
            return None
        if not isinstance(json_command, dict):
            await CONNECTIONS_MANAGER.send_message(
                websocket,
                f"Invalid type of the message: {type(json_command)}."
                ""
                """ Command must be a valid JSON mapping""",
            )
            return None

        try:
            rpc_message = RPCMessageModel(**json_command)
            return rpc_message
        except ValidationError as exception:
            errors = exception.value.errors()
            await CONNECTIONS_MANAGER.send_message(websocket, errors)
            return None

    async def send_message(self, websocket: WebSocket, message: str) -> None:
        """Send message"""
        _LOG.info(
            f'Meesage to send is "{message}"',
        )

        if isinstance(message, str):
            await websocket.send_text(message)
        elif isinstance(message, (dict, list)):
            try:
                await websocket.send_json(message)
            except TypeError:
                return
        else:
            raise TypeError("Unsupported message type")


CONNECTIONS_MANAGER = WebSocketConnectionManager()


@app.websocket("/")
async def exchange_rate(websocket: WebSocket):
    """
    Subscribe to relevant, up-to-date exchange rates
    """
    await CONNECTIONS_MANAGER.connect(websocket)
    client_service = (
        CONNECTIONS_MANAGER.get_exchange_rate_client_service(websocket)
    )
    try:
        while True:

            rpc_message = await CONNECTIONS_MANAGER.receive_command(websocket)
            if not rpc_message:
                continue

            match (rpc_message.action):
                case "assets":
                    async for message in client_service.rpc_assets_message():
                        await websocket.send_json(message.model_dump())

                case "subscribe":
                    await CONNECTIONS_MANAGER.send_message(websocket, f"Subscribed")
                    asset_id_field = "assetId"
                    asset_id = rpc_message.message.pop(asset_id_field, None)
                    if not asset_id:
                        await CONNECTIONS_MANAGER.send_message(
                            websocket, f'parameter "{asset_id_field}" is missing'
                        )
                        continue
                    # Fetch the Asset record
                    asset = await Asset.find(Asset.id == asset_id).first_or_none()
                    if not asset:
                        await CONNECTIONS_MANAGER.send_message(
                            websocket, f"The Asset with id={asset_id} is not found"
                        )
                        continue

                    # Subscribe
                    client_service.asset = asset
                    async def yield_exchange_rate_messages():
                        async for message in client_service.rpc_subscribe_message(
                            websocket
                        ):
                            await websocket.send_json(message.model_dump())
                    async def listen_to_asset_switch():
                        while True:
                            rpc_message = await CONNECTIONS_MANAGER.receive_command(websocket)
                            if not rpc_message:
                                continue
                            asset_id = rpc_message.message.pop(asset_id_field, None)
                            if not (rpc_message.action == "subscribe" and isinstance(asset_id, int)):
                                await websocket.send_json(
                                    {"errors": [{"msg": f'Invalid data format for asset switching'}]}
                                )
                                continue
                            asset = await Asset.find(Asset.id == asset_id).first_or_none()
                            client_service.asset = asset
                            continue
                    await asyncio.gather(
                        yield_exchange_rate_messages(),
                        listen_to_asset_switch(),
                    )
                case _:
                    await CONNECTIONS_MANAGER.send_message(
                        websocket, f'The "{rpc_message.action}" action is not supported'
                    )
    except WebSocketDisconnect:
        CONNECTIONS_MANAGER.disconnect(websocket)
