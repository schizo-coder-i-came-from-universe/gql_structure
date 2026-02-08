import datetime
import uuid
import pytest

from GraphTypeDefinitions import schema

from uoishelpers.schema.WhoAmIExtension import WhoAmIExtension
from uoishelpers.gqlpermissions.RolePermissionSchemaExtension import RolePermissionSchemaExtension
from utils.DBFeeder import get_demodata
from .shared import (
    createContext,
    fake_ug_client,
    prepare_demodata,
    prepare_in_memory_sqllite,
)
from DBDefinitions import NoteModel


class NoopWhoAmIExtension(WhoAmIExtension):
    """
    Avoid external UG calls while still populating the context the way the
    production WhoAmI extension would.
    """

    async def on_execute(self):
        ctx = self.execution_context.context
        ctx.setdefault(
            "user",
            {
                "id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003",
                "name": "John",
                "surname": "Newbie",
                "email": "john.newbie@world.com",
            },
        )
        ctx.setdefault("ug_client", fake_ug_client)
        yield


schema.extensions = [
    NoopWhoAmIExtension,
    RolePermissionSchemaExtension,
    *[
        ext
        for ext in schema.extensions
        if ext not in (WhoAmIExtension, RolePermissionSchemaExtension)
    ],
]


@pytest.mark.asyncio
async def test_note_by_id_matches_demo_data():
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)

    context_value = createContext(async_session_maker)
    demo_note = get_demodata()["notes_evolution"][0]
    note_id = str(demo_note["id"])

    query = """
        query($id: UUID!) {
            note: noteById(id: $id) {
                id
                title
                content
                createdbyId
            }
        }
    """
    resp = await schema.execute(
        query, variable_values={"id": note_id}, context_value=context_value
    )

    assert resp.errors is None
    payload = resp.data["note"]
    assert payload["id"] == note_id
    assert payload["title"] == demo_note["title"]
    assert payload["content"] == demo_note["content"]
    assert payload["createdbyId"] == str(demo_note["createdby_id"])


@pytest.mark.asyncio
async def test_note_crud_for_authenticated_user():
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)

    context_value = createContext(async_session_maker)
    acting_user_id = context_value["user"]["id"]

    insert_query = """
        mutation($title: String!, $content: String!) {
            result: noteInsert(note: {title: $title, content: $content}) {
                ... on NoteGQLModel {
                    id
                    title
                    content
                    lastchange
                    createdbyId
                    rbacobjectId
                }
                ... on InsertError {
                    msg
                    input
                }
            }
        }
    """
    insert_variables = {
        "title": "Integration note",
        "content": "This note is created via pre-startup tests.",
    }
    insert_resp = await schema.execute(
        insert_query, variable_values=insert_variables, context_value=context_value
    )

    assert insert_resp.errors is None
    insert_result = insert_resp.data["result"]
    assert insert_result is not None
    assert insert_result.get("title") == insert_variables["title"]
    assert insert_result.get("content") == insert_variables["content"]
    assert insert_result.get("createdbyId") == acting_user_id
    assert insert_result.get("rbacobjectId") == acting_user_id
    note_id = insert_result["id"]
    lastchange = insert_result["lastchange"]

    update_query = """
        mutation($id: UUID!, $lastchange: DateTime!, $title: String!) {
            result: noteUpdateOwn(
                note: {id: $id, lastchange: $lastchange, title: $title}
            ) {
                ... on NoteGQLModel {
                    id
                    title
                    lastchange
                    changedbyId
                }
                ... on NoteGQLModelUpdateError {
                    msg
                    input
                }
            }
        }
    """
    new_title = "Updated integration note"
    update_resp = await schema.execute(
        update_query,
        variable_values={
            "id": note_id,
            "lastchange": lastchange,
            "title": new_title,
        },
        context_value=context_value,
    )

    assert update_resp.errors is None
    update_result = update_resp.data["result"]
    assert update_result is not None
    assert update_result.get("title") == new_title
    assert update_result.get("changedbyId") == acting_user_id
    updated_lastchange = update_result["lastchange"]

    delete_query = """
        mutation($id: UUID!, $lastchange: DateTime!) {
            result: noteDeleteOwn(note: {id: $id, lastchange: $lastchange}) {
                msg
                input
            }
        }
    """
    delete_resp = await schema.execute(
        delete_query,
        variable_values={"id": note_id, "lastchange": updated_lastchange},
        context_value=context_value,
    )

    assert delete_resp.errors is None
    assert delete_resp.data["result"] is None


@pytest.mark.asyncio
async def test_note_update_rejects_stale_lastchange():
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)

    context_value = createContext(async_session_maker)

    insert_query = """
        mutation($title: String!, $content: String!) {
            result: noteInsert(note: {title: $title, content: $content}) {
                ... on NoteGQLModel {
                    id
                    lastchange
                }
                ... on InsertError {
                    msg
                }
            }
        }
    """
    insert_resp = await schema.execute(
        insert_query,
        variable_values={
            "title": "Locking note",
            "content": "Should refuse stale updates",
        },
        context_value=context_value,
    )

    assert insert_resp.errors is None
    insert_result = insert_resp.data["result"]
    note_id = insert_result["id"]
    initial_lastchange = insert_result["lastchange"]
    initial_lastchange_dt = datetime.datetime.fromisoformat(initial_lastchange)

    update_query = """
        mutation($id: UUID!, $lastchange: DateTime!, $title: String!) {
            result: noteUpdateOwn(
                note: {id: $id, lastchange: $lastchange, title: $title}
            ) {
                ... on NoteGQLModel {
                    id
                    title
                    lastchange
                }
                ... on NoteGQLModelUpdateError {
                    msg
                    failed
                }
            }
        }
    """
    first_update_resp = await schema.execute(
        update_query,
        variable_values={
            "id": note_id,
            "lastchange": initial_lastchange,
            "title": "Fresh title",
        },
        context_value=context_value,
    )

    assert first_update_resp.errors is None
    first_update_result = first_update_resp.data["result"]
    assert first_update_result["title"] == "Fresh title"
    updated_lastchange = first_update_result["lastchange"]
    updated_lastchange_dt = datetime.datetime.fromisoformat(updated_lastchange)

    # Simulate a concurrent change to force optimistic locking to fail.
    loader_session = context_value["loaders"].session
    row = await loader_session.get(NoteModel, uuid.UUID(note_id))
    row.lastchange = updated_lastchange_dt + datetime.timedelta(seconds=5)
    await loader_session.flush()
    assert row.lastchange != initial_lastchange_dt
    assert row.lastchange != updated_lastchange_dt

    stale_update_resp = await schema.execute(
        update_query,
        variable_values={
            "id": note_id,
            "lastchange": initial_lastchange,
            "title": "Stale title",
        },
        context_value=context_value,
    )

    assert stale_update_resp.errors is None
    stale_update_result = stale_update_resp.data["result"]
    assert stale_update_result["msg"] == "update failed"
    assert stale_update_result["failed"] is True
    assert updated_lastchange != stale_update_result.get("lastchange")


@pytest.mark.asyncio
async def test_note_update_and_delete_reject_non_admin():
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)

    owner_context = createContext(async_session_maker)

    insert_query = """
        mutation($title: String!, $content: String!) {
            result: noteInsert(note: {title: $title, content: $content}) {
                ... on NoteGQLModel {
                    id
                    lastchange
                }
            }
        }
    """
    insert_resp = await schema.execute(
        insert_query,
        variable_values={
            "title": "Owner note",
            "content": "Non-admin should not touch me",
        },
        context_value=owner_context,
    )

    assert insert_resp.errors is None
    insert_result = insert_resp.data["result"]
    note_id = insert_result["id"]
    note_lastchange = insert_result["lastchange"]

    intruder_context = createContext(async_session_maker)
    intruder_context["user"]["id"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeffffffff"

    update_query = """
        mutation($id: UUID!, $lastchange: DateTime!, $title: String!) {
            result: noteUpdateOwn(
                note: {id: $id, lastchange: $lastchange, title: $title}
            ) {
                ... on NoteGQLModel {
                    id
                    title
                }
                ... on NoteGQLModelUpdateError {
                    msg
                    failed
                }
            }
        }
    """
    intruder_update_resp = await schema.execute(
        update_query,
        variable_values={
            "id": note_id,
            "lastchange": note_lastchange,
            "title": "Intruder edit",
        },
        context_value=intruder_context,
    )

    assert intruder_update_resp.errors is None
    intruder_update_result = intruder_update_resp.data["result"]
    assert intruder_update_result["msg"] == "you can update only notes you created"
    assert intruder_update_result["failed"] is True

    delete_query = """
        mutation($id: UUID!, $lastchange: DateTime!) {
            result: noteDeleteOwn(note: {id: $id, lastchange: $lastchange}) {
                ... on NoteGQLModelDeleteError {
                    msg
                    failed
                }
            }
        }
    """
    intruder_delete_resp = await schema.execute(
        delete_query,
        variable_values={"id": note_id, "lastchange": note_lastchange},
        context_value=intruder_context,
    )

    assert intruder_delete_resp.errors is None
    intruder_delete_result = intruder_delete_resp.data["result"]
    assert intruder_delete_result["msg"] == "you can delete only notes you created"
    assert intruder_delete_result["failed"] is True
