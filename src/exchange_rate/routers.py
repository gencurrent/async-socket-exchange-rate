"""
Exchange rate application router
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from exchange_rate.client_service import AbstractExchangeRateClientService
from exchange_rate.models import RPCSubscribeMessageModel
from exchange_rate.utils import single_error_rpc_response
from rpc.models import RPCErrorMessageModel, RPCCommandModel
from rpc.connection_service import AbstractConnectionService, RPCConnectionService


router = APIRouter()


@router.websocket("/")
async def exchange_rate(websocket: WebSocket):
    """
    Subscribe to relevant, up-to-date exchange rates
    """
    connection_service: AbstractConnectionService = RPCConnectionService(websocket)
    await connection_service.connect()
    try:
        while True:
            await wait_and_handle_rpc_message(connection_service)
    except WebSocketDisconnect:
        pass
    finally:
        await connection_service.disconnect()


async def wait_and_handle_rpc_message(connection_service: AbstractConnectionService) -> None:
    """
    Wawit and handle a new incoming RPC message
    """
    rpc_message: RPCCommandModel = await connection_service.receive_command()

    client_service: AbstractExchangeRateClientService = connection_service.get_client_service()
    match (rpc_message.action):

        case "assets":
            last_rpc_command = connection_service.get_last_rpc_command()
            if last_rpc_command and last_rpc_command.action == "subscribe":
                await client_service.rpc_switch_asset_id(None)
            async for message in client_service.rpc_assets():
                await connection_service.send_message(message)

        case "subscribe":
            await handle_subscribe_action(connection_service, rpc_message)
        case _:
            error_rpc_response = single_error_rpc_response(rpc_message.action, "Unknown action")
            await connection_service.send_message(error_rpc_response)

    connection_service.set_last_rpc_command(rpc_message)


async def handle_subscribe_action(
    connection_service: AbstractConnectionService, rpc_message: RPCCommandModel
) -> asyncio.Task | None:
    try:
        rpc_subscribe_message_model = RPCSubscribeMessageModel(**rpc_message.message)
    except ValidationError as exception:
        error_message = RPCErrorMessageModel.from_validation_error(exception)
        await connection_service.send_message(error_message)
        return

    # Subscribe
    client_service: AbstractExchangeRateClientService = connection_service.get_client_service()
    error_message = await client_service.rpc_switch_asset_id(rpc_subscribe_message_model.asset_id)
    if error_message:
        await connection_service.send_message(error_message)
        return

    last_rpc_command = connection_service.get_last_rpc_command()
    if last_rpc_command and last_rpc_command.action == "subscribe":
        # Do not proceed if subscribed to another asset ID
        return

    # Wrap the async outputs into a single async function
    async def yield_exchange_rate_messages():
        async for message in client_service.rpc_subscribe():
            await connection_service.send_message(message)

    task = asyncio.create_task(yield_exchange_rate_messages())
    connection_service.add_task(task)
