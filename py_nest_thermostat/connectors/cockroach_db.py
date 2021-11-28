import logging
from contextlib import contextmanager

import sqlalchemy.ext.declarative as dec
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from py_nest_thermostat.connectors.base import BaseDbConnector
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
import os

SQLAlchemyBase = dec.declarative_base()

DB_CREDENTIALS_FILE = Path("~/.py-nest-thermostat/cockroad_db.env").expanduser()
load_dotenv(DB_CREDENTIALS_FILE)


class CockroachDbConnectionParams(BaseModel):
    password: str = os.getenv("password", "")
    username: str = os.getenv("username", "")
    port: str = os.getenv("port", "")
    database: str = os.getenv("database", "")
    host: str = os.getenv("host", "")
    cluster_name: str = os.getenv("cluster_name", "")
    ssl_cert_path: Path = Path("~/.postgresql/root.crt").expanduser().resolve()


class CockroachDatabaseConnector(BaseDbConnector):
    def __init__(self, connection_params: CockroachDbConnectionParams):
        self.connection_url: str = (
            f"cockroachdb://{connection_params.username}:"
            f"{connection_params.password}@{connection_params.host}:"
            f"{connection_params.port}/defaultdb?"
            f"sslmode=verify-full&sslrootcert={connection_params.ssl_cert_path}&"
            f"options=--cluster%3D{connection_params.cluster_name}"
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
            logging.debug("Closing database connection")
