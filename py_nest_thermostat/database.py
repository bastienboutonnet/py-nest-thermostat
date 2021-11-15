import logging
from contextlib import contextmanager

import sqlalchemy.ext.declarative as dec
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_NAME = "py-nest-thermostat-report"
DB_PASSWORD = "magical_password"
DB_USERNAME = "py-nest-thermostat"

DB_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@localhost:5432/{DB_NAME}"

SQLAlchemyBase = dec.declarative_base()


class Database:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

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


database_connector = Database(DB_URL)
