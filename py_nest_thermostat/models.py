from sqlalchemy import Column, DateTime, Float, String

from py_nest_thermostat.database import SQLAlchemyBase


class DeviceStats(SQLAlchemyBase):  # type: ignore
    __tablename__ = "device_stats"
    id = Column(String, primary_key=True)
    name = Column(String)
    recorded_at = Column(DateTime)
    humidity = Column(Float)
    temperature = Column(Float)
    mode = Column(String)
    target_temperature = Column(Float)
