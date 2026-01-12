# from uoishelpers.dataloaders import createIdLoader, createFkeyLoader
# from functools import cache

from src.DBDefinitions import BaseModel
from src.DBDefinitions import EventInvitationModel, EventModel, NoteModel

from uoishelpers.dataloaders.LoaderMapBase import LoaderMapBase
from uoishelpers.dataloaders.IDLoader import IDLoader
import src.DBDefinitions
import typing

class LoaderMap(LoaderMapBase[BaseModel]):
    """LoaderMap is a map of IDLoaders for all models in the BaseModel registry.
    It is used to create loaders for all models in the BaseModel registry.
    """
    BaseModel = BaseModel

    EventModel: IDLoader[src.DBDefinitions.EventModel] = None
    EventInvitationModel: IDLoader[src.DBDefinitions.EventInvitationModel] = None
    NoteModel: IDLoader[src.DBDefinitions.NoteModel] = None

    def __init__(self, session):
        super().__init__(session)

        self.EventModel = self.get(EventModel)
        self.EventInvitationModel = self.get(EventInvitationModel)
        self.NoteModel = self.get(NoteModel)

        # print(f"LoaderMap created with session: {session}")

def _ensure_session(session_or_factory: typing.Any):
    """
    IDLoader expects an AsyncSession instance. Accept either a session or a
    sessionmaker/factory and return an active session instance.
    """
    if hasattr(session_or_factory, "identity_map"):
        return session_or_factory
    if callable(session_or_factory):
        return session_or_factory()
    return session_or_factory

def createLoadersContext(session):
    real_session = _ensure_session(session)
    return {
        "loaders": LoaderMap(real_session)
    }
