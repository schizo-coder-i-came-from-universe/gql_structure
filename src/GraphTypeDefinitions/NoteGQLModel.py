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
    ScalarResolver,
    Update,
    UpdateError,
    createInputs2,
    getLoadersFromInfo,
    getUserFromInfo,
)

from .BaseGQLModel import BaseGQLModel, IDType


UserGQLModel = typing.Annotated["UserGQLModel", strawberry.lazy(".UserGQLModel")]
NoteGQLModelRef = typing.Annotated["NoteGQLModel", strawberry.lazy(".NoteGQLModel")]

NOTE_ALLOWED_ROLES = ["note-owner", "note-editor", "administrátor"]


class NoteInsertPrepareExtension(FieldExtension):
    """
    Normalizes owner information before the RBAC pipeline kicks in so that
    RbacInsertProviderExtension can pull a non-null rbacobject_id.
    """

    async def resolve_async(self, next_, source, info: strawberry.types.Info, *args, **kwargs):
        note_input = kwargs.get("note", None)
        if note_input is not None:
            owner_id = getattr(note_input, "owner_id", None)
            if owner_id is None:
                user = getUserFromInfo(info=info)
                owner_id = IDType(user["id"])
                note_input.owner_id = owner_id

            target_rbacobject = getattr(note_input, "rbacobject_id", None)
            if target_rbacobject is None:
                target_rbacobject = owner_id
                note_input.rbacobject_id = target_rbacobject

            if hasattr(note_input, "set_rbacobject_id"):
                note_input.set_rbacobject_id(target_rbacobject)

        return await next_(source, info, *args, **kwargs)


@createInputs2
class NoteInputFilter:
    id: IDType
    title: str
    content: str
    owner_id: IDType
    createdby_id: IDType


@strawberry.federation.type(description="A note entry", keys=["id"])
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



# region Notes query


@strawberry.type(description="Query support for notes")
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

    rbacobject_id: strawberry.Private[IDType] = None
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


@strawberry.type(description="Mutation support for notes")
class NoteMutation:
    @strawberry.field(
        description="Creates a note. Defaults owner to caller if omitted",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[InsertError, NoteGQLModel](
                roles=NOTE_ALLOWED_ROLES
            ),
            UserRoleProviderExtension[InsertError, NoteGQLModel](),
            RbacInsertProviderExtension[InsertError, NoteGQLModel](),
            NoteInsertPrepareExtension(),
        ],
    )
    async def note_insert(
        self,
        info: strawberry.types.Info,
        note: NoteInsertGQLModel,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
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
        note: NoteUpdateGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[NoteGQLModel, UpdateError[NoteGQLModel]]:
        user = getUserFromInfo(info=info)
        user_id = IDType(user["id"])
        note.changedby_id = user_id
        return await Update[NoteGQLModel].DoItSafeWay(info=info, entity=note)

    @strawberry.field(
        description="Deletes an existing note",
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
        note: NoteDeleteGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Optional[DeleteError[NoteGQLModel]]:
        return await Delete[NoteGQLModel].DoItSafeWay(info=info, entity=note)

# endregion
