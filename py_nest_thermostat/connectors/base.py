from abc import ABC

import sqlalchemy.ext.declarative as dec

SQLAlchemyBase = dec.declarative_base()


class BaseDbConnector(ABC):
    """
    Base database connector class
    """

    def __init__(self, connection_params: dict[str, str]):
        self.connection_params = connection_params

    def connect(self):
        "Connection method implement in concrete classes."
        ...

    def create_models(self):
        "Model creation method. Must be implemented in concretes."
        ...

    def session_manager(self):
        "context manager to be implemented in concrete classes."
        ...
