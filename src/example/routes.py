from __future__ import annotations

from typing import Annotated

from chassis_cache.manager import CacheManager
from chassis_repo.session import SessionDep
from chassis_storage.protocols import StorageBackend
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from example.schemas import (
    BookCreate,
    BookListResponse,
    BookResponse,
    BookUpdate,
    CoverUploadResponse,
    DeleteResponse,
    ErrorResponse,
    SearchResponse,
)
from example.services import BookService


def _get_cache(request: Request) -> CacheManager:
    return request.app.state.cache_manager


def _get_storage(request: Request) -> StorageBackend:
    return request.app.state.storage_backend


async def get_book_service(
    request: Request,
    session: SessionDep,
) -> BookService:
    """FastAPI dependency that constructs a BookService with injected dependencies."""
    cache: CacheManager = _get_cache(request)
    storage: StorageBackend = _get_storage(request)
    return BookService(session=session, cache=cache, storage=storage)


BookServiceDep: Annotated[BookService, Depends(get_book_service)] = Annotated[
    BookService, Depends(get_book_service)
]

book_router: APIRouter = APIRouter(prefix="/books", tags=["books"])


@book_router.get("/", response_model=BookListResponse)
async def list_books(
    svc: BookServiceDep,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> BookListResponse:
    """List books with optional search, sorting, and pagination."""
    return await svc.list_books(
        page=page, per_page=per_page, search=search, sort_by=sort_by, sort_dir=sort_dir,
    )


@book_router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    svc: BookServiceDep,
) -> BookResponse:
    """Get a single book by ID."""
    book: BookResponse | None = await svc.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


@book_router.post("/", response_model=BookResponse, status_code=201)
async def create_book(
    svc: BookServiceDep,
    title: str = Form(...),
    author: str = Form(...),
    isbn: str | None = Form(None),
    description: str | None = Form(None),
) -> BookResponse:
    """Create a new book."""
    data: BookCreate = BookCreate(
        title=title, author=author, isbn=isbn, description=description,
    )
    return await svc.create_book(data)


@book_router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    svc: BookServiceDep,
    title: str | None = Form(None),
    author: str | None = Form(None),
    isbn: str | None = Form(None),
    description: str | None = Form(None),
) -> BookResponse:
    """Update a book. Only provided fields are updated."""
    data: BookUpdate = BookUpdate(
        title=title, author=author, isbn=isbn, description=description,
    )
    book: BookResponse | None = await svc.update_book(book_id, data)
    if book is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    return book


@book_router.delete("/{book_id}", response_model=DeleteResponse)
async def delete_book(
    book_id: int,
    svc: BookServiceDep,
) -> DeleteResponse:
    """Delete a book."""
    deleted: bool = await svc.delete_book(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return DeleteResponse(deleted=True)


@book_router.post("/{book_id}/cover", response_model=CoverUploadResponse, status_code=201)
async def upload_book_cover(
    book_id: int,
    svc: BookServiceDep,
    file: UploadFile = File(...),
) -> CoverUploadResponse:
    """Upload a cover image for a book."""
    result: CoverUploadResponse | None = await svc.upload_cover(book_id, file)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return result


@book_router.get("/{book_id}/cover")
async def get_book_cover(
    book_id: int,
    svc: BookServiceDep,
) -> Response:
    """Get a book's cover image."""
    cover: tuple[bytes, str] | None = await svc.get_cover(book_id)
    if cover is None:
        raise HTTPException(status_code=404, detail="Cover not found")
    content, media_type = cover
    return Response(content=content, media_type=media_type)


@book_router.get("/search/{query}", response_model=SearchResponse)
async def search_books(
    query: str,
    svc: BookServiceDep,
) -> SearchResponse:
    """Search books by title."""
    return await svc.search_books(query)
