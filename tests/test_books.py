"""Integration tests for the Book Library API.

Uses SQLite (file-based) for database tests. No Docker required.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from httpx import Response


@pytest.fixture(autouse=True)
def _test_config() -> Generator[None, None, None]:
    """Force SQLite and InMemory cache for testing so Docker is not required."""
    os.environ["CHASSIS_DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mktemp()}.db"
    os.environ["CHASSIS_REDIS_URL"] = ""  # Use InMemory cache during tests
    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a TestClient with lifespan support (table creation on startup)."""
    from main import create_app

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestBookCRUD:
    def test_list_books_empty(self, client: TestClient) -> None:
        response: Response = client.get("/books/")
        assert response.status_code == 200
        body: dict = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_create_and_get_book(self, client: TestClient) -> None:
        response: Response = client.post(
            "/books/",
            data={"title": "Test Book", "author": "Author Name", "isbn": "1234567890"},
        )
        assert response.status_code == 201
        body: dict = response.json()
        book_id: int = body["id"]
        assert body["title"] == "Test Book"

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Test Book"
        assert body["author"] == "Author Name"
        assert body["isbn"] == "1234567890"

    def test_update_book(self, client: TestClient) -> None:
        response: Response = client.post(
            "/books/", data={"title": "Old Title", "author": "Author"}
        )
        book_id: int = response.json()["id"]

        response = client.put(
            f"/books/{book_id}",
            data={"title": "New Title", "description": "A description"},
        )
        assert response.status_code == 200
        body: dict = response.json()
        assert body["title"] == "New Title"
        assert body["description"] == "A description"

    def test_delete_book(self, client: TestClient) -> None:
        response: Response = client.post(
            "/books/", data={"title": "To Delete", "author": "Author"}
        )
        book_id: int = response.json()["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 404

    def test_get_nonexistent_book(self, client: TestClient) -> None:
        response: Response = client.get("/books/9999")
        assert response.status_code == 404

    def test_list_books_pagination(self, client: TestClient) -> None:
        for i in range(5):
            client.post("/books/", data={"title": f"Book {i}", "author": f"Author {i}"})

        response: Response = client.get("/books/?page=1&per_page=3")
        body: dict = response.json()
        assert len(body["items"]) == 3
        assert body["total"] == 5
        assert body["pages"] == 2

    def test_search_books(self, client: TestClient) -> None:
        client.post("/books/", data={"title": "Python Cookbook", "author": "Author"})
        client.post("/books/", data={"title": "Rust Programming", "author": "Author"})
        client.post(
            "/books/", data={"title": "Deep Learning with Python", "author": "Author"}
        )

        response: Response = client.get("/books/search/Python")
        body: dict = response.json()
        assert body["total"] == 2


class TestAuth:
    def test_phone_send_code(self, client: TestClient) -> None:
        response: Response = client.post(
            "/auth/phone/send", json={"phone": "13800138000"}
        )
        assert response.status_code == 200
        assert "send_id" in response.json()

    def test_phone_verify_with_mock_code(self, client: TestClient) -> None:
        response: Response = client.post(
            "/auth/phone/send", json={"phone": "13800138000"}
        )
        send_id: str = response.json()["send_id"]

        response = client.post(
            "/auth/phone/verify", json={"send_id": send_id, "code": "1234"}
        )
        assert response.status_code == 200
        body: dict = response.json()
        assert body["user"]["provider_id"] == "phone:13800138000"

    def test_phone_verify_wrong_code(self, client: TestClient) -> None:
        response: Response = client.post(
            "/auth/phone/send", json={"phone": "13800138000"}
        )
        send_id: str = response.json()["send_id"]

        response = client.post(
            "/auth/phone/verify", json={"send_id": send_id, "code": "0000"}
        )
        assert response.status_code == 400

    def test_email_send_code(self, client: TestClient) -> None:
        response: Response = client.post(
            "/auth/email/send", json={"email": "user@example.com"}
        )
        assert response.status_code == 200
        assert "send_id" in response.json()

    def test_email_verify_with_mock_code(self, client: TestClient) -> None:
        response: Response = client.post(
            "/auth/email/send", json={"email": "user@example.com"}
        )
        send_id: str = response.json()["send_id"]

        response = client.post(
            "/auth/email/verify", json={"send_id": send_id, "code": "1234"}
        )
        assert response.status_code == 200
        body: dict = response.json()
        assert body["user"]["provider_id"] == "email:user@example.com"

    def test_oauth_login_redirect(self, client: TestClient) -> None:
        response: Response = client.get(
            "/auth/demo/login?redirect_uri=http://localhost:8000/callback",
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert "demo_code" in response.headers["location"]

    def test_oauth_callback(self, client: TestClient) -> None:
        login_response: Response = client.get(
            "/auth/demo/login?redirect_uri=http://localhost:8000/callback",
            follow_redirects=False,
        )
        location: str = login_response.headers["location"]
        state: str = location.split("state=")[1]

        response: Response = client.get(
            f"/auth/demo/callback?code=demo_code&state={state}"
        )
        assert response.status_code == 200
        body: dict = response.json()
        assert "Welcome, Demo User!" in body["message"]


class TestStorage:
    def test_upload_cover(self, client: TestClient) -> None:
        response: Response = client.post(
            "/books/", data={"title": "Book With Cover", "author": "Author"}
        )
        book_id: int = response.json()["id"]

        response = client.post(
            f"/books/{book_id}/cover",
            files={"file": ("cover.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        assert response.status_code == 201
        body: dict = response.json()
        assert body["cover_file_id"] is not None
        assert body["url"] is not None

        response = client.get(f"/books/{book_id}/cover")
        assert response.status_code == 200
        assert response.content == b"fake-image-bytes"


class TestAdmin:
    def test_admin_login_page(self, client: TestClient) -> None:
        response: Response = client.get("/admin/login")
        assert response.status_code == 200

    def test_admin_login_success(self, client: TestClient) -> None:
        response: Response = client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert response.status_code in (200, 302, 307)

    def test_admin_login_failure(self, client: TestClient) -> None:
        response: Response = client.post(
            "/admin/login",
            data={"username": "admin", "password": "wrong"},
        )
        assert response.status_code in (200, 401)
