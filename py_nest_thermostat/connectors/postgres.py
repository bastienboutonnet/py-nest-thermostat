import logging
from contextlib import contextmanager

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from py_nest_thermostat.config import PyNestConfig, config
from py_nest_thermostat.connectors.base import BaseDbConnector, SQLAlchemyBase


class PostgresDbConnectionParams(BaseModel):
    db_name: str = "py-nest-thermostat-report"
    password: str = "magical_password"
    username: str = "py-nest-thermostat"


class PostgresDatabaseConnector(BaseDbConnector):
    def __init__(self, config: PyNestConfig):
        self.connection_params = PostgresDbConnectionParams(**config.database.credentials)

        db_url: str = (
            f"postgresql+psycopg2://{self.connection_params.username}:"
            f"{self.connection_params.password}@localhost:5432/{self.connection_params.db_name}"
        )
        self.connection_string = db_url

    def connect(self):
        self.engine = create_engine(self.connection_string)
        self.engine.connect()
        self.session_factory = sessionmaker(bind=self.engine)

    def create_models(self):
        import py_nest_thermostat.models  # noqa: F401

        SQLAlchemyBase.metadata.create_all(self.engine)

    @contextmanager
    def session_manager(self):
        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            logging.error("Rolling back transaction")
            session.rollback()
            raise e
        finally:
            logging.debug("Closing database connection")


postgres_connector = PostgresDatabaseConnector(config)
