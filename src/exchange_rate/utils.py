"""
Echange Rate utils
"""

from typing import Any, Dict

from rpc.models import RPCMessageModel


def single_error_rpc_response(action: str, error: str | Dict[Any, Any]) -> RPCMessageModel:
    """Return an RPC response based on the single error"""
    error_mesage = {"errors": [{"msg": error}]}
    return RPCMessageModel(action=action, message=error_mesage)
