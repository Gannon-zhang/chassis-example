from __future__ import annotations

import datetime
from typing import Final

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__: Final[str] = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True, default=None)
    cover_file_id: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now
    )
