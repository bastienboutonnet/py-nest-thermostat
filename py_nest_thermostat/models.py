import uuid

from sqlalchemy import Column, DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID

from py_nest_thermostat.connectors.base import SQLAlchemyBase


class DeviceStats(SQLAlchemyBase):  # type: ignore
    __tablename__ = "device_stats"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    recorded_at = Column(DateTime)
    humidity = Column(Float)
    temperature = Column(Float)
    mode = Column(String)
    target_temperature = Column(Float)
