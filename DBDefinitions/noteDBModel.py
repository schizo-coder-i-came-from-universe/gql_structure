import datetime
from sqlalchemy.schema import Column
from sqlalchemy import Uuid, Text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY

from .baseDBModel import BaseModel
from .uuid import uuid


class NoteModel(BaseModel):
    __tablename__ = "notes"

    id = Column(Uuid, primary_key=True, comment="primary key", default=uuid)
    author_id = Column(
        Uuid,
        index=True,
        nullable=False,
        comment="creator of the note",
    )
    body = Column(Text, nullable=False, comment="text content of the note")
    can_edit = Column(
        ARRAY(Uuid),
        nullable=False,
        default=list,
        comment="user ids allowed to edit the note",
    )
    can_read = Column(
        ARRAY(Uuid),
        nullable=False,
        default=list,
        comment="user ids allowed to read the note",
    )
    blocked = Column(
        ARRAY(Uuid),
        nullable=False,
        default=list,
        comment="user ids explicitly denied access",
    )
    created = Column(DateTime, default=datetime.datetime.now, comment="creation time")
    lastchange = Column(
        DateTime,
        default=datetime.datetime.now,
        comment="moment of the last update",
    )
