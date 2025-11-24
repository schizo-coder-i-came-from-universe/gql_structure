import datetime
import typing
import strawberry

import strawberry.types
from src.DBDefinitions.NoteDBModel import NotePermissionLevel

from uoishelpers.gqlpermissions import OnlyForAuthentized
from uoishelpers.resolvers import (
    getLoadersFromInfo,
    getUserFromInfo,
    createInputs2,
    InputModelMixin,
    Insert,
    InsertError,
    Update,
    UpdateError,
    Delete,
    DeleteError,
    PageResolver,
    VectorResolver,
    ScalarResolver,
)
from uoishelpers.gqlpermissions.LoadDataExtension import LoadDataExtension

from .BaseGQLModel import BaseGQLModel, IDType


NotePermissionLevelGQL = strawberry.enum(
    NotePermissionLevel,
    name="NotePermissionLevel",
    description="Defines how a user can interact with a note",
)

UserGQLModel = typing.Annotated["UserGQLModel", strawberry.lazy(".UserGQLModel")]
NoteGQLModelRef = typing.Annotated["NoteGQLModel", strawberry.lazy(".NoteGQLModel")]
NotePermissionGQLModelRef = typing.Annotated[
    "NotePermissionGQLModel", strawberry.lazy(".NoteGQLModel")
]


@createInputs2
class NoteInputFilter:
    id: IDType
    title: str
    content: str
    owner_id: IDType
    createdby_id: IDType


@createInputs2
class NotePermissionInputFilter:
    id: IDType
    note_id: IDType
    user_id: IDType
    permission_level: NotePermissionLevelGQL
    note: NoteInputFilter = strawberry.field(
        description="""Allows filtering based on properties of the related note"""
    )


@strawberry.federation.type(
    description="Describes permissions assigned to users for a note", keys=["id"]
)
class NotePermissionGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).NotePermissionModel

    note_id: typing.Optional[IDType] = strawberry.field(
        description="Note owned by the permission entry",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )
    user_id: typing.Optional[IDType] = strawberry.field(
        description="User holding the permission",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )
    permission_level: typing.Optional[NotePermissionLevelGQL] = strawberry.field(
        description="Permission level",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    note: typing.Optional[NoteGQLModelRef] = strawberry.field(
        description="Reference to the note",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[NoteGQLModelRef](fkey_field_name="note_id"),
    )

    user: typing.Optional[UserGQLModel] = strawberry.field(
        description="Reference to the user with permissions",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[UserGQLModel](fkey_field_name="user_id"),
    )


@strawberry.federation.type(description="A note with optional permissions", keys=["id"])
class NoteGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).NoteModel

    title: typing.Optional[str] = strawberry.field(
        description="Human readable title of the note",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )
    content: typing.Optional[str] = strawberry.field(
        description="Note text content",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )
    owner_id: typing.Optional[IDType] = strawberry.field(
        description="Owner of the note",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    owner: typing.Optional[UserGQLModel] = strawberry.field(
        description="Resolved owner of the note",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[UserGQLModel](fkey_field_name="owner_id"),
    )

    permissions: typing.List[NotePermissionGQLModelRef] = strawberry.field(
        description="Explicit permission entries for the note",
        permission_classes=[OnlyForAuthentized],
        resolver=VectorResolver[NotePermissionGQLModelRef](
            fkey_field_name="note_id", whereType=NotePermissionInputFilter
        ),
    )

    @staticmethod
    async def _users_with_permission(
        info: strawberry.types.Info,
        note_id: IDType,
        level: NotePermissionLevel,
    ) -> typing.List[UserGQLModel]:
        loader = getLoadersFromInfo(info).NotePermissionModel
        permission_rows = await loader.filter_by(note_id=note_id)
        result: typing.List[UserGQLModel] = []
        for row in permission_rows:
            if row.permission_level == level and row.user_id is not None:
                result.append(UserGQLModel(id=row.user_id))
        return result

    @strawberry.field(
        description="Users that can edit the note",
        permission_classes=[OnlyForAuthentized],
    )
    async def editors(
        self, info: strawberry.types.Info
    ) -> typing.List[UserGQLModel]:
        return await self._users_with_permission(
            info=info, note_id=self.id, level=NotePermissionLevel.EDIT
        )

    @strawberry.field(
        description="Users that can only read the note",
        permission_classes=[OnlyForAuthentized],
    )
    async def readers(
        self, info: strawberry.types.Info
    ) -> typing.List[UserGQLModel]:
        return await self._users_with_permission(
            info=info, note_id=self.id, level=NotePermissionLevel.READ
        )

    @strawberry.field(
        description="Users explicitly blocked from seeing the note",
        permission_classes=[OnlyForAuthentized],
    )
    async def blocked_users(
        self, info: strawberry.types.Info
    ) -> typing.List[UserGQLModel]:
        return await self._users_with_permission(
            info=info, note_id=self.id, level=NotePermissionLevel.BLOCKED
        )


# region Notes query


@strawberry.type(description="Query support for notes and their permissions")
class NoteQuery:
    note_by_id: typing.Optional[NoteGQLModel] = strawberry.field(
        description="Fetches note by its identifier",
        permission_classes=[OnlyForAuthentized],
        resolver=NoteGQLModel.load_with_loader,
    )

    note_page: typing.List[NoteGQLModel] = strawberry.field(
        description="Returns notes matching given criteria",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[NoteGQLModel](whereType=NoteInputFilter),
    )

    note_permission_by_id: typing.Optional[NotePermissionGQLModelRef] = (
        strawberry.field(
            description="Fetches a single permission entry by id",
            permission_classes=[OnlyForAuthentized],
            resolver=NotePermissionGQLModel.load_with_loader,
        )
    )

    note_permission_page: typing.List[NotePermissionGQLModelRef] = strawberry.field(
        description="Returns permission entries matching filters",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[NotePermissionGQLModelRef](
            whereType=NotePermissionInputFilter
        ),
    )


# endregion

# region Notes mutations


@strawberry.input(description="Input type for creating a note")
class NoteInsertGQLModel(InputModelMixin):
    getLoader = NoteGQLModel.getLoader

    id: typing.Optional[IDType] = strawberry.field(
        description="Client provided note id", default=None
    )
    title: typing.Optional[str] = strawberry.field(
        description="Note title", default=None
    )
    content: typing.Optional[str] = strawberry.field(
        description="Note content", default=None
    )
    owner_id: typing.Optional[IDType] = strawberry.field(
        description="Owner identifier, defaults to current user", default=None
    )

    createdby_id: strawberry.Private[IDType] = None
    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Input type for updating a note")
class NoteUpdateGQLModel:
    id: IDType = strawberry.field(description="Note identifier")
    lastchange: datetime.datetime = strawberry.field(description="timestamp")
    title: typing.Optional[str] = strawberry.field(description="Note title", default=None)
    content: typing.Optional[str] = strawberry.field(
        description="Note content", default=None
    )
    owner_id: typing.Optional[IDType] = strawberry.field(
        description="Owner identifier", default=None
    )

    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Input type for deleting a note")
class NoteDeleteGQLModel:
    id: IDType = strawberry.field(description="Note identifier")
    lastchange: datetime.datetime = strawberry.field(description="timestamp")


@strawberry.input(description="Input type for creating permission entries")
class NotePermissionInsertGQLModel(InputModelMixin):
    getLoader = NotePermissionGQLModel.getLoader

    id: typing.Optional[IDType] = strawberry.field(
        description="Client provided id", default=None
    )
    note_id: IDType = strawberry.field(description="Related note identifier")
    user_id: IDType = strawberry.field(description="User receiving the permission")
    permission_level: NotePermissionLevelGQL = strawberry.field(
        description="Assigned permission level"
    )

    createdby_id: strawberry.Private[IDType] = None
    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Input type for updating permission entries")
class NotePermissionUpdateGQLModel:
    id: IDType = strawberry.field(description="Permission identifier")
    lastchange: datetime.datetime = strawberry.field(description="timestamp")
    permission_level: typing.Optional[NotePermissionLevelGQL] = strawberry.field(
        description="New permission level", default=None
    )

    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Input type for deleting permission entries")
class NotePermissionDeleteGQLModel:
    id: IDType = strawberry.field(description="Permission identifier")
    lastchange: datetime.datetime = strawberry.field(description="timestamp")


async def _user_can_manage_note(
    info: strawberry.types.Info, note_row: typing.Any, user_id: IDType
) -> bool:
    if note_row.owner_id == user_id:
        return True

    loader = getLoadersFromInfo(info).NotePermissionModel
    permissions = await loader.filter_by(note_id=note_row.id)
    for permission in permissions:
        if (
            permission.user_id == user_id
            and permission.permission_level == NotePermissionLevel.EDIT
        ):
            return True
    return False


@strawberry.type(description="Mutation support for notes and their permissions")
class NoteMutation:
    @strawberry.field(
        description="Creates a note. Defaults owner to caller if omitted",
        permission_classes=[OnlyForAuthentized],
    )
    async def note_insert(
        self, info: strawberry.types.Info, note: NoteInsertGQLModel
    ) -> typing.Union[NoteGQLModel, InsertError[NoteGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        note.createdby_id = user_id
        note.changedby_id = user_id
        if note.owner_id is None:
            note.owner_id = user_id
        return await Insert[NoteGQLModel].DoItSafeWay(info=info, entity=note)

    @strawberry.field(
        description="Updates an existing note",
        permission_classes=[OnlyForAuthentized],
        extensions=[LoadDataExtension[UpdateError, NoteGQLModel]()],
    )
    async def note_update(
        self,
        info: strawberry.types.Info,
        note: NoteUpdateGQLModel,
        db_row: typing.Any,
    ) -> typing.Union[NoteGQLModel, UpdateError[NoteGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        if not await _user_can_manage_note(info=info, note_row=db_row, user_id=user_id):
            return UpdateError[NoteGQLModel](
                msg="You are not allowed to update this note",
                code="2a6eac73-ef4b-4bed-aad9-1fe952e2e412",
                location="note_update",
                _entity=db_row,
                _input=note,
            )
        note.changedby_id = user_id
        return await Update[NoteGQLModel].DoItSafeWay(info=info, entity=note)

    @strawberry.field(
        description="Deletes an existing note",
        permission_classes=[OnlyForAuthentized],
        extensions=[LoadDataExtension[DeleteError, NoteGQLModel]()],
    )
    async def note_delete(
        self,
        info: strawberry.types.Info,
        note: NoteDeleteGQLModel,
        db_row: typing.Any,
    ) -> typing.Optional[DeleteError[NoteGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        if db_row.owner_id != user_id:
            return DeleteError[NoteGQLModel](
                msg="Only owner can delete the note",
                code="33e2a9b2-21f4-49d8-b4c0-2a48247c657c",
                location="note_delete",
                _entity=db_row,
                _input=note,
            )
        return await Delete[NoteGQLModel].DoItSafeWay(info=info, entity=note)

    @strawberry.field(
        description="Creates a permission entry for a note",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            LoadDataExtension[InsertError, NoteGQLModel](
                getLoader=NoteGQLModel.getLoader, primary_key_name="note_id"
            )
        ],
    )
    async def note_permission_insert(
        self,
        info: strawberry.types.Info,
        permission: NotePermissionInsertGQLModel,
        db_row: typing.Any,
    ) -> typing.Union[
        NotePermissionGQLModel, InsertError[NotePermissionGQLModel]
    ]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        if db_row.owner_id != user_id:
            return InsertError[NotePermissionGQLModel](
                msg="Only note owner can manage permissions",
                code="597c4ba5-0e74-4f97-b7cc-e0b477aa4ae9",
                location="note_permission_insert",
                _input=permission,
            )
        permission.createdby_id = user_id
        permission.changedby_id = user_id
        return await Insert[NotePermissionGQLModel].DoItSafeWay(
            info=info, entity=permission
        )

    @strawberry.field(
        description="Updates a permission entry",
        permission_classes=[OnlyForAuthentized],
        extensions=[LoadDataExtension[UpdateError, NotePermissionGQLModel]()],
    )
    async def note_permission_update(
        self,
        info: strawberry.types.Info,
        permission: NotePermissionUpdateGQLModel,
        db_row: typing.Any,
    ) -> typing.Union[
        NotePermissionGQLModel, UpdateError[NotePermissionGQLModel]
    ]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        note_loader = getLoadersFromInfo(info).NoteModel
        note_row = await note_loader.load(db_row.note_id)
        if note_row is None or note_row.owner_id != user_id:
            return UpdateError[NotePermissionGQLModel](
                msg="Only note owner can update permissions",
                code="e62dc413-95d7-43f4-9684-2559ab03cf50",
                location="note_permission_update",
                _entity=db_row,
                _input=permission,
            )
        permission.changedby_id = user_id
        return await Update[NotePermissionGQLModel].DoItSafeWay(
            info=info, entity=permission
        )

    @strawberry.field(
        description="Deletes a permission entry",
        permission_classes=[OnlyForAuthentized],
        extensions=[LoadDataExtension[DeleteError, NotePermissionGQLModel]()],
    )
    async def note_permission_delete(
        self,
        info: strawberry.types.Info,
        permission: NotePermissionDeleteGQLModel,
        db_row: typing.Any,
    ) -> typing.Optional[DeleteError[NotePermissionGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        note_loader = getLoadersFromInfo(info).NoteModel
        note_row = await note_loader.load(db_row.note_id)
        if note_row is None or note_row.owner_id != user_id:
            return DeleteError[NotePermissionGQLModel](
                msg="Only note owner can delete permissions",
                code="dd90ba57-2680-4d73-8b51-7044b3b85bd1",
                location="note_permission_delete",
                _entity=db_row,
                _input=permission,
            )
        return await Delete[NotePermissionGQLModel].DoItSafeWay(
            info=info, entity=permission
        )


# endregion
