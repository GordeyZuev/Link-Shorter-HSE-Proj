"""Сервис сокращения ссылок."""

import logging
import os
import secrets
import string
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger("app")

ALPHABET = string.ascii_lowercase + string.digits
CODE_LENGTH = 6
MAX_ATTEMPTS = 10
NAME_LIMIT = 100
RESERVED = {"health", "docs", "redoc", "links", "info", "version"}

links: dict[str, dict] = {}


def reset_storage() -> None:
    links.clear()


def find_by_url(url: str) -> dict | None:
    for item in links.values():
        if item["url"] == url:
            return item
    return None


def make_code() -> str | None:
    for _ in range(MAX_ATTEMPTS):
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if code not in links and code not in RESERVED:
            return code
    return None


def add_link(url: str, name: str) -> dict | None:
    link_id = make_code()
    if link_id is None:
        return None
    item = {"id": link_id, "url": url, "name": name}
    links[link_id] = item
    return item


def get_link(link_id: str) -> dict | None:
    return links.get(link_id)


def update_name(link_id: str, name: str) -> dict | None:
    item = links.get(link_id)
    if item is None:
        return None
    item["name"] = name
    return item


def delete_link(link_id: str) -> bool:
    if link_id not in links:
        return False
    del links[link_id]
    return True


def clean_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Адрес должен начинаться с http:// или https://",
        )
    return cleaned


def clean_name(name: str | None) -> str:
    if name is None:
        return ""
    cleaned = name.strip()
    if len(cleaned) > NAME_LIMIT:
        raise HTTPException(status_code=400, detail="Подпись длиннее 100 символов")
    return cleaned


def short_url(link_id: str) -> str:
    base = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base}/{link_id}"


def to_public(item: dict) -> dict:
    return {
        "id": item["id"],
        "name": item["name"],
        "url": item["url"],
        "short_url": short_url(item["id"]),
    }


class LinkCreate(BaseModel):
    url: str
    name: str | None = None


class LinkUpdate(BaseModel):
    name: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    logger.info("Сервис запущен")
    yield
    logger.info("Сервис остановлен")


app = FastAPI(title="Сокращатель ссылок", lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Сервис сокращения ссылок работает"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": os.getenv("APP_VERSION", "0.1.0")}


@app.get("/info")
def info():
    return {
        "app_name": os.getenv("APP_NAME", "Сокращатель ссылок"),
        "author": os.getenv("APP_AUTHOR", "Не указан"),
    }


@app.post("/links")
def create_link(body: LinkCreate):
    url = clean_url(body.url)
    existing = find_by_url(url)
    if existing is not None:
        logger.info("Адрес уже сохранён id=%s", existing["id"])
        return JSONResponse(to_public(existing), status_code=200)

    item = add_link(url, clean_name(body.name))
    if item is None:
        raise HTTPException(status_code=503, detail="Свободные короткие коды закончились")

    logger.info("Создана ссылка id=%s", item["id"])
    return JSONResponse(to_public(item), status_code=201)


@app.get("/links")
def list_links():
    return [to_public(item) for item in links.values()]


@app.get("/links/{link_id}")
def read_link(link_id: str):
    item = get_link(link_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    return to_public(item)


@app.patch("/links/{link_id}")
def rename_link(link_id: str, body: LinkUpdate):
    item = update_name(link_id, clean_name(body.name))
    if item is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    logger.info("Обновлено имя id=%s", link_id)
    return to_public(item)


@app.delete("/links/{link_id}", status_code=204)
def remove_link(link_id: str):
    if not delete_link(link_id):
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    logger.info("Удалена ссылка id=%s", link_id)


@app.get("/{link_id}")
def follow(link_id: str = Path(pattern=r"^[a-z0-9]{6}$")):
    item = get_link(link_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    logger.info("Переход id=%s", link_id)
    return RedirectResponse(item["url"], status_code=302)
