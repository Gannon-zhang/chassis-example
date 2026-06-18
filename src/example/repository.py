from __future__ import annotations

from chassis_repo.base import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession

from example.models import Book


class BookRepository(BaseRepository[Book]):
    """Typed repository for Book entities.

    Inherits CRUD from BaseRepository: get_by_id, list, create, update, delete.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Book)
