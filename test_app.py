import re

import pytest
from fastapi.testclient import TestClient

from app_final import app, reset_storage

client = TestClient(app)


def create_link(url, name=None):
    payload = {"url": url}
    if name is not None:
        payload["name"] = name
    return client.post("/links", json=payload)


@pytest.fixture(autouse=True)
def clean_storage():
    reset_storage()
    yield
    reset_storage()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Сервис сокращения ссылок работает"


def test_version(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "9.9.9")

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": "9.9.9"}


def test_info(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Тестовый сервис")
    monkeypatch.setenv("APP_AUTHOR", "Анна")

    response = client.get("/info")

    assert response.status_code == 200
    assert response.json() == {
        "app_name": "Тестовый сервис",
        "author": "Анна",
    }


def test_create_link(monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://127.0.0.1:8000")

    response = create_link("https://www.hse.ru", "Расписание")

    assert response.status_code == 201
    body = response.json()
    assert re.fullmatch(r"[a-z0-9]{6}", body["id"])
    assert body["name"] == "Расписание"
    assert body["url"] == "https://www.hse.ru"
    assert body["short_url"] == f"http://127.0.0.1:8000/{body['id']}"


def test_read_link():
    created = create_link("https://www.hse.ru").json()

    response = client.get(f"/links/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_duplicate_url():
    first = create_link("https://www.hse.ru")
    second = create_link("https://www.hse.ru", "Другое имя")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_bad_url():
    response = create_link("www.hse.ru")

    assert response.status_code == 400


def test_redirect():
    created = create_link("https://www.hse.ru").json()

    response = client.get(f"/{created['id']}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://www.hse.ru"


def test_rename():
    created = create_link("https://www.hse.ru", "Старое").json()

    response = client.patch(f"/links/{created['id']}", json={"name": "Новое"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Новое"
    assert body["url"] == created["url"]


def test_delete():
    created = create_link("https://www.hse.ru").json()

    response = client.delete(f"/links/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/links/{created['id']}").status_code == 404
    assert client.get(f"/{created['id']}", follow_redirects=False).status_code == 404


def test_unknown_link():
    assert client.get("/links/missing").status_code == 404
    assert client.get("/zzzzzz", follow_redirects=False).status_code == 404


def test_list_links():
    first = create_link("https://example.com/one").json()
    second = create_link("https://example.com/two").json()

    response = client.get("/links")

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {first["id"], second["id"]}


def test_strips_url():
    response = create_link("  https://example.com/path  ")

    assert response.status_code == 201
    assert response.json()["url"] == "https://example.com/path"


def test_duplicate_keeps_name():
    first = create_link("https://example.com/same", "Первое")
    second = create_link("https://example.com/same", "Второе")

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["name"] == "Первое"


def test_trailing_slash_is_different():
    first = create_link("https://example.com/slash")
    second = create_link("https://example.com/slash/")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_name_too_long():
    created = create_link("https://example.com/long").json()

    response = client.patch(f"/links/{created['id']}", json={"name": "я" * 101})

    assert response.status_code == 400


def test_second_delete():
    created = create_link("https://example.com/gone").json()

    assert client.delete(f"/links/{created['id']}").status_code == 204
    assert client.delete(f"/links/{created['id']}").status_code == 404
