import datetime
import typing

import strawberry
import strawberry.types
from strawberry.extensions import FieldExtension

from uoishelpers.gqlpermissions import OnlyForAuthentized
from uoishelpers.gqlpermissions.LoadDataExtension import LoadDataExtension
from uoishelpers.gqlpermissions.RbacInsertProviderExtension import (
    RbacInsertProviderExtension,
)
from uoishelpers.gqlpermissions.RbacProviderExtension import RbacProviderExtension
from uoishelpers.gqlpermissions.UserAccessControlExtension import (
    UserAccessControlExtension,
)
from uoishelpers.gqlpermissions.UserRoleProviderExtension import (
    UserRoleProviderExtension,
)
from uoishelpers.resolvers import (
    Delete,
    DeleteError,
    Insert,
    InsertError,
    InputModelMixin,
    PageResolver,
    Update,
    UpdateError,
    createInputs2,
    getLoadersFromInfo,
    getUserFromInfo,
)

from .BaseGQLModel import BaseGQLModel, IDType


UserGQLModel = typing.Annotated["UserGQLModel", strawberry.lazy(".UserGQLModel")]

NOTE_ALLOWED_ROLES = ["note-owner", "note-editor", "administrátor"]
#NOTE_ALLOWED_ROLES = ["note-owner", "note-editor"]

class NoteInsertPrepareExtension(FieldExtension):
    """
    Ensures rbacobject_id is derived from the authenticated user
    before the RBAC pipeline kicks in.
    """

    async def resolve_async(self, next_, source, info: strawberry.types.Info, *args, **kwargs):
        note_input = kwargs.get("note", None)
        if note_input is not None:
            target_rbacobject = getattr(note_input, "rbacobject_id", None)
            if target_rbacobject is None:
                user = getUserFromInfo(info=info)
                target_rbacobject = IDType(user["id"])
                note_input.rbacobject_id = target_rbacobject

            if hasattr(note_input, "set_rbacobject_id"):
                note_input.set_rbacobject_id(target_rbacobject)

        return await next_(source, info, *args, **kwargs)


@createInputs2
class NoteInputFilter:
    id: IDType = strawberry.field(description="Filters a single note by its unique identifier")
    title: str = strawberry.field(
        description="Filters by the note title; supports the standard string operators used in other filters"
    )
    content: str = strawberry.field(description="Filters notes whose content matches the provided condition")
    createdby_id: IDType = strawberry.field(description="Filters notes by the creator's user id")


@strawberry.federation.type(
    description="A user-owned free-form note that can store a title and text content",
    keys=["id"],
)
class NoteGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).NoteModel

    title: typing.Optional[str] = strawberry.field(
        description="Human readable title shown in note listings",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )
    content: typing.Optional[str] = strawberry.field(
        description="Full text content of the note (plain text or markdown)",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )


# region Notes query


@strawberry.type(description="Queries for reading notes")
class NoteQuery:
    note_by_id: typing.Optional[NoteGQLModel] = strawberry.field(
        description="Fetches a single note by its identifier (returns null when the note is not visible)",
        permission_classes=[OnlyForAuthentized],
        resolver=NoteGQLModel.load_with_loader,
    )

    note_page: typing.List[NoteGQLModel] = strawberry.field(
        description="Returns notes matching the provided filter (title/content/creator)",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[NoteGQLModel](whereType=NoteInputFilter),
    )

# endregion

# region Notes mutations


@strawberry.input(description="Input type for creating a note owned by the authenticated user")
class NoteInsertGQLModel(InputModelMixin):
    getLoader = NoteGQLModel.getLoader

    id: typing.Optional[IDType] = strawberry.field(
        description="Client provided note id (omit to let the server generate one)", default=None
    )
    title: typing.Optional[str] = strawberry.field(
        description="Note title", default=None
    )
    content: typing.Optional[str] = strawberry.field(
        description="Note content", default=None
    )
    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None
    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(
    description="Input type for updating a note using optimistic locking via lastchange"
)
class NoteUpdateGQLModel:
    id: IDType = strawberry.field(description="Note identifier")
    lastchange: datetime.datetime = strawberry.field(
        description="Last known timestamp of the note used for optimistic locking"
    )
    title: typing.Optional[str] = strawberry.field(description="Note title", default=None)
    content: typing.Optional[str] = strawberry.field(
        description="Note content", default=None
    )
    


@strawberry.input(
    description="Input type for deleting a note; requires the last known timestamp to avoid deleting a stale version"
)
class NoteDeleteGQLModel:
    id: IDType = strawberry.field(description="Note identifier")
    lastchange: datetime.datetime = strawberry.field(
        description="Last known timestamp of the note used for optimistic locking"
    )


@strawberry.type(description="Mutation support for notes")
class NoteMutation:
    @strawberry.field(
        description="Creates a note owned by the authenticated user",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserRoleProviderExtension[InsertError, NoteGQLModel](),
            RbacInsertProviderExtension[InsertError, NoteGQLModel](),
            NoteInsertPrepareExtension(),
        ],
    )
    async def note_insert(
        self,
        info: strawberry.types.Info,
        note: NoteInsertGQLModel = strawberry.argument(
            description="Payload with the title/content values for the new note"
        ),
        rbacobject_id: IDType = strawberry.argument(
            description="RBAC object id derived from the note; injected by RBAC extensions"
        ),
        user_roles: typing.List[dict] = strawberry.argument(
            description="Caller roles injected by UserRoleProviderExtension"
        ),
    ) -> typing.Union[NoteGQLModel, InsertError[NoteGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        note.createdby_id = user_id
        note.changedby_id = user_id
        return await Insert[NoteGQLModel].DoItSafeWay(info=info, entity=note)

    @strawberry.field(
        description="Updates an existing note",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[UpdateError, NoteGQLModel](
                roles=NOTE_ALLOWED_ROLES
            ),
            UserRoleProviderExtension[UpdateError, NoteGQLModel](),
            RbacProviderExtension[UpdateError, NoteGQLModel](),
            LoadDataExtension[UpdateError, NoteGQLModel](),
        ],
    )
    async def note_update(
        self,
        info: strawberry.types.Info,
        note: NoteUpdateGQLModel = strawberry.argument(
            description="Note payload including id and lastchange to be updated"
        ),
        db_row: typing.Any = strawberry.argument(
            description="Existing note row loaded by LoadDataExtension"
        ),
        rbacobject_id: IDType = strawberry.argument(
            description="RBAC object id of the target note resolved by RBAC extensions"
        ),
        user_roles: typing.List[dict] = strawberry.argument(
            description="Caller roles injected by UserRoleProviderExtension"
        ),
    ) -> typing.Union[NoteGQLModel, UpdateError[NoteGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        note.changedby_id = user_id
        return await Update[NoteGQLModel].DoItSafeWay(info=info, entity=note)

    @strawberry.field(
        description="Updates an existing note created by the caller",
        permission_classes=[OnlyForAuthentized],
        extensions=[LoadDataExtension[UpdateError, NoteGQLModel]()],
    )
    async def note_update_own(
        self,
        info: strawberry.types.Info,
        note: NoteUpdateGQLModel = strawberry.argument(
            description="Note payload including id and lastchange to be updated"
        ),
        db_row: typing.Any = strawberry.argument(
            description="Existing note row loaded by LoadDataExtension"
        ),
    ) -> typing.Union[NoteGQLModel, UpdateError[NoteGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])

        is_owner = getattr(db_row, "createdby_id", None) == user_id
        if not is_owner:
            return UpdateError[NoteGQLModel](
                _entity=db_row,
                msg="you can update only notes you created",
                _input=note,
            )

        return await Update[NoteGQLModel].DoItSafeWay(info=info, entity=note)

    @strawberry.field(
        description="Deletes an existing note using optimistic locking via lastchange",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[DeleteError, NoteGQLModel](
                roles=NOTE_ALLOWED_ROLES
            ),
            UserRoleProviderExtension[DeleteError, NoteGQLModel](),
            RbacProviderExtension[DeleteError, NoteGQLModel](),
            LoadDataExtension[DeleteError, NoteGQLModel](),
        ],
    )
    async def note_delete(
        self,
        info: strawberry.types.Info,
        note: NoteDeleteGQLModel = strawberry.argument(
            description="Target note identifier with the lastchange timestamp"
        ),
        db_row: typing.Any = strawberry.argument(
            description="Existing note row loaded by LoadDataExtension"
        ),
        rbacobject_id: IDType = strawberry.argument(
            description="RBAC object id of the target note resolved by RBAC extensions"
        ),
        user_roles: typing.List[dict] = strawberry.argument(
            description="Caller roles injected by UserRoleProviderExtension"
        ),
    ) -> typing.Optional[DeleteError[NoteGQLModel]]:
        return await Delete[NoteGQLModel].DoItSafeWay(info=info, entity=note)

    @strawberry.field(
        description="Deletes a note created by the caller using optimistic locking",
        permission_classes=[OnlyForAuthentized],
        extensions=[LoadDataExtension[DeleteError, NoteGQLModel]()],
    )
    async def note_delete_own(
        self,
        info: strawberry.types.Info,
        note: NoteDeleteGQLModel = strawberry.argument(
            description="Target note identifier with the lastchange timestamp"
        ),
        db_row: typing.Any = strawberry.argument(
            description="Existing note row loaded by LoadDataExtension"
        ),
    ) -> typing.Optional[DeleteError[NoteGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])

        is_owner = getattr(db_row, "createdby_id", None) == user_id
        if not is_owner:
            return DeleteError[NoteGQLModel](
                _entity=db_row,
                msg="you can delete only notes you created",
                _input=note,
            )

        return await Delete[NoteGQLModel].DoItSafeWay(info=info, entity=note)

# endregion
