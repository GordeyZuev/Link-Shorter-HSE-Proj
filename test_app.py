import pytest
from fastapi.testclient import TestClient

from app_final import app, reset_storage

client = TestClient(app)


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
