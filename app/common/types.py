from typing import Union, Any
from pydantic import BaseModel, Field, TypeAdapter
from typing import Literal, List, Annotated, Optional
from datetime import datetime
from pydantic import model_validator, ConfigDict, field_serializer
from uuid import uuid4
from enum import Enum
from typing_extensions import Self

class MissingAPIKeyError(Exception):
    """Exception for missing API key(s)"""

    def __init__(self, missing_keys: list[str]):
        message = f"Please check your API keys. Missing keys: {', '.join(missing_keys)}"
        super().__init__(message)
        self.missing_keys = missing_keys
