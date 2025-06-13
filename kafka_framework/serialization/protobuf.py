"""
Protobuf serializer implementation.
"""

try:
    from google.protobuf import json_format
    from google.protobuf.message import Message
except ImportError:
    json_format = None
    Message = None

from ..exceptions import SerializationError
from .base import BaseSerializer


class ProtobufSerializer(BaseSerializer):
    """
    Protobuf serializer.
    Requires the [protobuf] extra to be installed.
    """

    def __init__(
        self,
        message_type: type[Message],
        include_default_values: bool = False,
        preserving_proto_field_name: bool = True,
    ):
        if json_format is None:
            raise ImportError(
                "protobuf is not installed. Install kafka-framework[protobuf] to use ProtobufSerializer."
            )

        if not issubclass(message_type, Message):
            raise ValueError("message_type must be a Protobuf Message class")

        self.message_type = message_type
        self.include_default_values = include_default_values
        self.preserving_proto_field_name = preserving_proto_field_name

    async def serialize(
        self,
        value: dict | Message,
    ) -> bytes:
        """Serialize a value to Protobuf bytes."""
        try:
            if isinstance(value, dict):
                # Convert dict to Protobuf message
                message = self.message_type()
                json_format.ParseDict(
                    value,
                    message,
                    ignore_unknown_fields=True,
                )
            elif isinstance(value, self.message_type):
                message = value
            else:
                raise ValueError(f"Value must be either a dict or {self.message_type.__name__}")

            return message.SerializeToString()

        except Exception as e:
            raise SerializationError(f"Failed to serialize to Protobuf: {e}") from e

    async def deserialize(
        self,
        value: bytes,
    ) -> dict | Message:
        """Deserialize Protobuf bytes to a value."""
        try:
            message = self.message_type()
            message.ParseFromString(value)
            return message

        except Exception as e:
            raise SerializationError(f"Failed to deserialize from Protobuf: {e}") from e

    def message_to_dict(self, message: Message) -> dict:
        """Convert a Protobuf message to a dictionary."""
        return json_format.MessageToDict(
            message,
            including_default_value_fields=self.include_default_values,
            preserving_proto_field_name=self.preserving_proto_field_name,
        )

    def dict_to_message(self, data: dict) -> Message:
        """Convert a dictionary to a Protobuf message."""
        message = self.message_type()
        json_format.ParseDict(data, message, ignore_unknown_fields=True)
        return message
