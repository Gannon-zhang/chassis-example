from __future__ import annotations

import json

from chassis_cache.manager import CacheManager
from chassis_repo.filters import PaginatedResult, Pagination, QueryFilter, Sort
from chassis_storage.models import StoredFile
from chassis_storage.protocols import StorageBackend
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from example.models import Book
from example.repository import BookRepository
from example.schemas import (
    BookCreate,
    BookListResponse,
    BookResponse,
    BookUpdate,
    CoverUploadResponse,
    SearchResponse,
)


class BookService:
    """Business logic for book management.

    Orchestrates repository access, cache management, and file storage.
    All I/O goes through injected dependencies.
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: CacheManager,
        storage: StorageBackend,
    ) -> None:
        self._repo: BookRepository = BookRepository(session)
        self._cache: CacheManager = cache
        self._storage: StorageBackend = storage

    @staticmethod
    def _model_to_response(book: Book) -> BookResponse:
        return BookResponse(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn,
            description=book.description,
            cover_file_id=book.cover_file_id,
            created_at=book.created_at.isoformat() if book.created_at else None,
            updated_at=book.updated_at.isoformat() if book.updated_at else None,
        )

    async def list_books(
        self,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> BookListResponse:
        cache_key: str = f"book_list:{page}:{per_page}:{search}:{sort_by}:{sort_dir}"

        cached_raw: bytes | None = await self._cache.get("books", cache_key)
        if cached_raw is not None:
            data: dict[str, object] = json.loads(cached_raw)
            return BookListResponse(**data)

        filters: list[QueryFilter] = []
        if search:
            filters.append(
                QueryFilter(field="title", op="like", value=f"%{search}%")
            )

        sorts: list[Sort] = [
            Sort(field=sort_by, direction="asc" if sort_dir == "asc" else "desc")
        ]

        result: PaginatedResult[Book] = await self._repo.list(
            filters=filters if filters else None,
            sort=sorts,
            pagination=Pagination(page=page, per_page=per_page),
        )

        response: BookListResponse = BookListResponse(
            items=[self._model_to_response(b) for b in result.items],
            total=result.total,
            page=result.page,
            per_page=result.per_page,
            pages=result.pages,
        )

        await self._cache.set(
            "books", cache_key, response.model_dump_json().encode(), ttl=30
        )
        return response

    async def get_book(self, book_id: int) -> BookResponse | None:
        cache_key: str = f"book:{book_id}"

        cached_raw: bytes | None = await self._cache.get("books", cache_key)
        if cached_raw is not None:
            data: dict[str, object] = json.loads(cached_raw)
            return BookResponse(**data)

        book: Book | None = await self._repo.get_by_id(book_id)
        if book is None:
            return None

        response: BookResponse = self._model_to_response(book)
        await self._cache.set(
            "books", cache_key, response.model_dump_json().encode(), ttl=60
        )
        return response

    async def create_book(self, data: BookCreate) -> BookResponse:
        book: Book = await self._repo.create(data.model_dump(exclude_none=True))
        await self._cache.delete("books", "book_list")
        return self._model_to_response(book)

    async def update_book(self, book_id: int, data: BookUpdate) -> BookResponse | None:
        update_data: dict[str, object] = data.model_dump(exclude_none=True)
        if not update_data:
            return None

        book: Book = await self._repo.update(book_id, update_data)
        await self._cache.delete("books", f"book:{book_id}")
        await self._cache.delete("books", "book_list")
        return self._model_to_response(book)

    async def delete_book(self, book_id: int) -> bool:
        deleted: bool = await self._repo.delete(book_id)
        if deleted:
            await self._cache.delete("books", f"book:{book_id}")
            await self._cache.delete("books", "book_list")
        return deleted

    async def upload_cover(self, book_id: int, file: UploadFile) -> CoverUploadResponse | None:
        book: Book | None = await self._repo.get_by_id(book_id)
        if book is None:
            return None

        content: bytes = await file.read()
        content_type: str = file.content_type or "application/octet-stream"

        stored: StoredFile = await self._storage.store(
            filename=file.filename or f"cover_{book_id}",
            content=content,
            content_type=content_type,
        )

        await self._repo.update(book_id, {"cover_file_id": stored.id})
        await self._cache.delete("books", f"book:{book_id}")
        await self._cache.delete("books", "book_list")

        stored_url: str | None = await self._storage.url(stored.id)
        return CoverUploadResponse(cover_file_id=stored.id, url=stored_url)

    async def get_cover(self, book_id: int) -> tuple[bytes, str] | None:
        book: Book | None = await self._repo.get_by_id(book_id)
        if book is None or book.cover_file_id is None:
            return None

        cover_bytes: bytes | None = await self._storage.get(book.cover_file_id)
        if cover_bytes is None:
            return None

        # Get content type from stored file metadata if possible
        return cover_bytes, "image/*"

    async def search_books(self, query: str) -> SearchResponse:
        result: PaginatedResult[Book] = await self._repo.list(
            filters=[
                QueryFilter(field="title", op="like", value=f"%{query}%")
            ],
            pagination=Pagination(page=1, per_page=50),
        )

        return SearchResponse(
            query=query,
            items=[self._model_to_response(b) for b in result.items],
            total=result.total,
        )
