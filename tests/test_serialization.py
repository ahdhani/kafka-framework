import pytest

from kafka_framework.serialization.avro import AvroSerializer

fastavro = pytest.importorskip("fastavro")


@pytest.mark.asyncio
async def test_avro_roundtrip():
    schema = {"type": "record", "name": "Test", "fields": [{"name": "field", "type": "string"}]}
    serializer = AvroSerializer(schema_registry_url="http://localhost", schema_dict=schema)
    value = {"field": "value"}
    data = await serializer.serialize(value)
    result = await serializer.deserialize(data)
    assert result == value
