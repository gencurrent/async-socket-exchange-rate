"""
DB exceptions
"""

from dataclasses import dataclass


@dataclass
class ModelException(Exception):
    """Custom application-level model exception"""

    message: str = "General model exception"


class AlreadyPopulatedException(ModelException):
    """The model instances have already been initialized"""

    message: str = "The model data is already populated"
