from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from .BaseModel import BaseModel, UUIDFKey, IDType


class NoteModel(BaseModel):
    __tablename__ = "notes_evolution"

    title: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
