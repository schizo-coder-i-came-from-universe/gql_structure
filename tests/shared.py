import asyncio
import re
import sqlalchemy
import sys

# setting path
sys.path.append("../gql_events")

import pytest

# from ..uoishelpers.uuid import UUIDColumn

from DBDefinitions import BaseModel, EventInvitationModel, EventModel, NoteModel


async def prepare_in_memory_sqllite():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    asyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # asyncEngine = create_async_engine("sqlite+aiosqlite:///data.sqlite")
    async with asyncEngine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async_session_maker = sessionmaker(
        asyncEngine, expire_on_commit=False, class_=AsyncSession
    )

    return async_session_maker


from utils.DBFeeder import get_demodata


async def prepare_demodata(async_session_maker):
    data = get_demodata()

    from uoishelpers.feeders import ImportModels

    await ImportModels(
        async_session_maker,
        [
            EventModel,
            EventInvitationModel,
            NoteModel,
        ],
        data,
    )


from utils.Dataloaders import createLoadersContext
from uoishelpers.schema.ProfilingExtension import Counter as ProfilingCounter
from typing import Any, Dict

async def fake_ug_client(query: str, variables: Dict[str, Any] | None = None):
    aliases = re.findall(r"item\d+", query)
    if "userCanWithState" in query or "userCanWithoutState" in query:
        payload = {"result": True}
    elif "roles(" in query or "roles " in query:
        payload = {"result": []}
    else:
        payload = {}
    return {"data": {alias: payload for alias in aliases}}

class DummyRoleLoader:
    async def load(self, params):
        return {"result": []}

class DummyAccessLoader:
    async def load(self, params):
        return {"result": True}

def createContext(asyncSessionMaker, withuser=True):
    loadersContext = createLoadersContext(asyncSessionMaker)
    loadersContext["ProfilingExtension.counter"] = ProfilingCounter()
    loadersContext["ug_client"] = fake_ug_client
    loadersContext["userRolesForRBACQuery_loader"] = DummyRoleLoader()
    loadersContext["userCanWithState_loader"] = DummyAccessLoader()
    loadersContext["userCanWithoutState_loader"] = DummyAccessLoader()
    user = {
        "id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003",
        "name": "John",
        "surname": "Newbie",
        "email": "john.newbie@world.com"
    }
    if withuser:
        loadersContext["user"] = user
    
    return loadersContext

def createInfo(asyncSessionMaker, withuser=True):
    class Request():
        @property
        def headers(self):
            return {"Authorization": "Bearer 2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
        
    class Info():
        @property
        def context(self):
            context = createContext(asyncSessionMaker, withuser=withuser)
            context["request"] = Request()
            return context
        
    return Info()
