import enum
from typing import Optional

import sqlalchemy
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .BaseModel import BaseModel, UUIDFKey, IDType


class NotePermissionLevel(enum.Enum):
    EDIT = "edit"
    READ = "read"
    BLOCKED = "blocked"


class NoteModel(BaseModel):
    __tablename__ = "notes_evolution"

    title: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    owner_id: Mapped[IDType] = UUIDFKey(
        ForeignKey("users.id"),
        nullable=False,
        comment="id of user owning the note",
    )

    permissions = relationship(
        "NotePermissionModel",
        back_populates="note",
        cascade="all, delete-orphan",
    )


class NotePermissionModel(BaseModel):
    __tablename__ = "note_permissions_evolution"
    __table_args__ = (
        UniqueConstraint(
            "note_id",
            "user_id",
            name="uq_note_permissions_note_user",
        ),
    )

    note_id: Mapped[IDType] = mapped_column(
        ForeignKey("notes_evolution.id"),
        nullable=False,
        default=None,
        comment="referenced note",
    )
    user_id: Mapped[IDType] = UUIDFKey(
        ForeignKey("users.id"),
        nullable=False,
        default=None,
        comment="user with configured permission",
    )
    permission_level: Mapped[NotePermissionLevel] = mapped_column(
        sqlalchemy.Enum(NotePermissionLevel, name="note_permission_level"),
        nullable=False,
        default=NotePermissionLevel.READ,
        comment="what the user can do with the note",
    )

    note = relationship(
        "NoteModel",
        back_populates="permissions",
        uselist=False,
    )
