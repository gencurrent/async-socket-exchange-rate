"""
Echange Rate utils
"""

from typing import Any, Dict

from rpc.models import RPCCommandModel


def single_error_rpc_response(action: str, error: str | Dict[Any, Any]) -> RPCCommandModel:
    """Return an RPC response based on the single error"""
    error_mesage = {"errors": [{"msg": error}]}
    return RPCCommandModel(action=action, message=error_mesage)
