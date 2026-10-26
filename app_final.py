"""Сервис сокращения ссылок."""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

logger = logging.getLogger("app")

links: dict[str, dict] = {}


def reset_storage() -> None:
    links.clear()


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
