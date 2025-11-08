import datetime
import typing
import uuid

import strawberry

from utils.Dataloaders import getLoadersFromInfo
from .permissions import NoteCanRead, NoteCanEdit

UserGQLModel = typing.Annotated["UserGQLModel", strawberry.lazy(".userGQLModel")]


@strawberry.federation.type(
    keys=["id"],
    description="""Entity representing a personal note""",
)
class NoteGQLModel:
    @classmethod
    async def resolve_reference(
        cls,
        info: strawberry.types.Info,
        id: uuid.UUID,
    ):
        result = None
        if id is not None:
            loaders = getLoadersFromInfo(info)
            noteloader = loaders.notes
            result = await noteloader.load(id=id)
        return result

    @strawberry.field(description="""Primary key""")
    def id(self) -> uuid.UUID:
        return self.id

    @strawberry.field(
        description="""The textual content of the note""",
        permission_classes=[NoteCanRead],
    )
    def body(self) -> str:
        return self.body

    @strawberry.field(description="""Identifier of the author""")
    def author_id(self) -> uuid.UUID:
        return self.author_id

    @strawberry.field(
        description="""User that created the note""",
        permission_classes=[NoteCanRead],
    )
    async def author(
        self, info: strawberry.types.Info
    ) -> typing.Optional["UserGQLModel"]:
        if self.author_id is None:
            return None
        return await UserGQLModel.resolve_reference(id=self.author_id)

    @strawberry.field(
        description="""Users allowed to edit the note""",
        permission_classes=[NoteCanEdit],
    )
    def editable_by(self) -> typing.List[uuid.UUID]:
        return list(self.can_edit or [])

    @strawberry.field(
        description="""Users allowed to read the note""",
        permission_classes=[NoteCanEdit],
    )
    def readable_by(self) -> typing.List[uuid.UUID]:
        return list(self.can_read or [])

    @strawberry.field(
        description="""Users that cannot access the note""",
        permission_classes=[NoteCanEdit],
    )
    def blocked_users(self) -> typing.List[uuid.UUID]:
        return list(self.blocked or [])

    @strawberry.field(
        description="""Moment when the note was created""",
        permission_classes=[NoteCanRead],
    )
    def created(self) -> typing.Optional[datetime.datetime]:
        return self.created

    @strawberry.field(
        description="""Timestamp / token for optimistic locking""",
        permission_classes=[NoteCanRead],
    )
    def lastchange(self) -> typing.Optional[datetime.datetime]:
        return self.lastchange


@strawberry.field(description="""Returns a note""")
async def note_by_id(
    info: strawberry.types.Info,
    id: uuid.UUID,
) -> typing.Optional[NoteGQLModel]:
    return await NoteGQLModel.resolve_reference(info, id)


@strawberry.input(description="Definition of note used for creation")
class NoteInsertGQLModel:
    body: str = strawberry.field(description="Text content of the note")
    author_id: uuid.UUID = strawberry.field(description="Author identifier")
    id: typing.Optional[uuid.UUID] = strawberry.field(
        description="Primary key (UUID), could be client generated",
        default=None,
    )
    can_edit: typing.List[uuid.UUID] = strawberry.field(
        description="Users allowed to edit",
        default_factory=list,
    )
    can_read: typing.List[uuid.UUID] = strawberry.field(
        description="Users allowed to read",
        default_factory=list,
    )
    blocked: typing.List[uuid.UUID] = strawberry.field(
        description="Users explicitly denied access",
        default_factory=list,
    )


@strawberry.input(description="Definition of note used for update")
class NoteUpdateGQLModel:
    id: uuid.UUID = strawberry.field(
        description="Primary key (UUID), identifies object of operation"
    )
    lastchange: datetime.datetime = strawberry.field(
        description="Timestamp / token for multiuser updates"
    )
    body: typing.Optional[str] = strawberry.field(
        description="Updated text content",
        default=None,
    )
    can_edit: typing.Optional[typing.List[uuid.UUID]] = strawberry.field(
        description="Users allowed to edit",
        default=None,
    )
    can_read: typing.Optional[typing.List[uuid.UUID]] = strawberry.field(
        description="Users allowed to read",
        default=None,
    )
    blocked: typing.Optional[typing.List[uuid.UUID]] = strawberry.field(
        description="Users explicitly denied access",
        default=None,
    )


@strawberry.type(description="Result of CUD operation on note")
class NoteResultGQLModel:
    id: typing.Optional[uuid.UUID] = None
    msg: str = strawberry.field(
        description="Result of the operation ok / fail",
        default="",
    )

    @strawberry.field(description="""Returns the note""")
    async def note(self, info: strawberry.types.Info) -> NoteGQLModel:
        return await NoteGQLModel.resolve_reference(info, self.id)


@strawberry.mutation(description="Write new note into database")
async def note_insert(
    self,
    info: strawberry.types.Info,
    note: NoteInsertGQLModel,
) -> NoteResultGQLModel:
    loader = getLoadersFromInfo(info).notes
    row = await loader.insert(note)
    result = NoteResultGQLModel()
    result.msg = "ok"
    result.id = row.id
    return result


@strawberry.mutation(
    description="Update the note in database",
    permission_classes=[NoteCanEdit],
)
async def note_update(
    self,
    info: strawberry.types.Info,
    note: NoteUpdateGQLModel,
) -> NoteResultGQLModel:
    loader = getLoadersFromInfo(info).notes
    row = await loader.update(note)
    result = NoteResultGQLModel()
    result.id = note.id
    if row is None:
        result.msg = "fail"
    else:
        result.msg = "ok"
    return result
