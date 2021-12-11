import logging
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from py_nest_thermostat.config import PyNestConfig, config
from py_nest_thermostat.connectors.base import BaseDbConnector, SQLAlchemyBase


class CockroachDbConnectionParams(BaseModel):
    password: str
    username: str
    port: str
    database: str
    host: str
    cluster_name: str
    ssl_cert_path: Path = Path("~/.postgresql/root.crt").expanduser().resolve()


class CockroachDatabaseConnector(BaseDbConnector):
    def __init__(self, config: PyNestConfig):
        self.connection_params = CockroachDbConnectionParams(**config.database.credentials)
        self.connection_url: str = (
            f"cockroachdb://{self.connection_params.username}:"
            f"{self.connection_params.password}@{self.connection_params.host}:"
            f"{self.connection_params.port}/defaultdb?"
            f"sslmode=verify-full&sslrootcert={self.connection_params.ssl_cert_path}&"
            f"options=--cluster%3D{self.connection_params.cluster_name}"
        )

    def connect(self):
        self.engine = create_engine(self.connection_url)
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
            session.close()
            logging.debug("Closing database connection")


cockroach_connector = CockroachDatabaseConnector(config)
