import strawberry

from .EventGQLModel import EventQuery
from .EventInvitationGQLModel import EventInvitationQuery
from .NoteGQLModel import NoteQuery

@strawberry.type(description="""Type for query root""")
class Query(EventQuery, EventInvitationQuery, NoteQuery):
    @strawberry.field(
        description="""Returns hello world"""
        )
    async def hello(
        self,
        info: strawberry.types.Info,
    ) -> str:
        return "hello world"
