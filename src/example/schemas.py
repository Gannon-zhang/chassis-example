from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    """Request schema for creating a book."""

    title: str = Field(..., min_length=1, max_length=200, examples=["The Great Gatsby"])
    author: str = Field(..., min_length=1, max_length=100, examples=["F. Scott Fitzgerald"])
    isbn: str | None = Field(None, max_length=20, examples=["9780743273565"])
    description: str | None = Field(None, max_length=2000)


class BookUpdate(BaseModel):
    """Request schema for updating a book. All fields optional."""

    title: str | None = Field(None, min_length=1, max_length=200)
    author: str | None = Field(None, min_length=1, max_length=100)
    isbn: str | None = Field(None, max_length=20)
    description: str | None = Field(None, max_length=2000)


class BookResponse(BaseModel):
    """Response schema for a single book."""

    id: int
    title: str
    author: str
    isbn: str | None
    description: str | None
    cover_file_id: str | None
    created_at: str | None
    updated_at: str | None

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    """Response schema for paginated book listings."""

    items: list[BookResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CoverUploadResponse(BaseModel):
    """Response schema for cover image upload."""

    cover_file_id: str
    url: str | None


class SearchResponse(BaseModel):
    """Response schema for book search."""

    query: str
    items: list[BookResponse]
    total: int


class DeleteResponse(BaseModel):
    """Response schema for delete operations."""

    deleted: bool


class ErrorResponse(BaseModel):
    """Standard error envelope (matches chassis exception handler format)."""

    error: dict[str, object]
