import logging
import typing
import uuid

import strawberry
from strawberry.permission import BasePermission
from strawberry.types import Info

from utils.Dataloaders import getUserFromInfo, getLoadersFromInfo


class SensitiveInfo(BasePermission):
    message = "User is not allowed to read sensitive info"

    async def has_permission(self, source: typing.Any, info: Info, **kwargs) -> bool:
        user = getUserFromInfo(info)
        result = False
        if user is not None:
            if user["id"] == "2d9dc5ca-a4a2-11ed-b9df-0242ac120003":
                result = True
        logging.info(f"{user} attempt to get sensitive information")
        return result


class NotePermissionBase(BasePermission):
    message = "User is not allowed to access this note"

    def _user_id(self, info: Info) -> typing.Optional[uuid.UUID]:
        user = getUserFromInfo(info)
        if user is None:
            return None
        raw_id = user.get("id")
        if raw_id is None:
            return None
        if isinstance(raw_id, uuid.UUID):
            return raw_id
        try:
            return uuid.UUID(str(raw_id))
        except (ValueError, TypeError):
            return None

    async def _get_note(
        self,
        source: typing.Any,
        info: Info,
        kwargs: dict,
    ):
        if source is not None:
            return source
        note_input = kwargs.get("note")
        note_id = getattr(note_input, "id", None)
        if note_id is None:
            note_id = kwargs.get("id")
        if note_id is None:
            return None
        loaders = getLoadersFromInfo(info)
        return await loaders.notes.load(id=note_id)

    def _is_blocked(self, note, user_id: uuid.UUID) -> bool:
        blocked = getattr(note, "blocked", None) or []
        return user_id in blocked

    def _can_edit(self, note, user_id: uuid.UUID) -> bool:
        if note.author_id == user_id:
            return True
        can_edit = getattr(note, "can_edit", None) or []
        return user_id in can_edit

    def _can_read(self, note, user_id: uuid.UUID) -> bool:
        if self._can_edit(note, user_id):
            return True
        can_read = getattr(note, "can_read", None) or []
        return user_id in can_read


class NoteCanRead(NotePermissionBase):
    message = "User is not allowed to read this note"

    async def has_permission(self, source: typing.Any, info: Info, **kwargs) -> bool:
        user_id = self._user_id(info)
        if user_id is None:
            return False
        note = await self._get_note(source, info, kwargs)
        if note is None:
            return False
        if self._is_blocked(note, user_id):
            return False
        return self._can_read(note, user_id)


class NoteCanEdit(NotePermissionBase):
    message = "User is not allowed to edit this note"

    async def has_permission(self, source: typing.Any, info: Info, **kwargs) -> bool:
        user_id = self._user_id(info)
        if user_id is None:
            return False
        note = await self._get_note(source, info, kwargs)
        if note is None:
            return False
        if self._is_blocked(note, user_id):
            return False
        return self._can_edit(note, user_id)
