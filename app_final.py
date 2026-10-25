"""Сервис сокращения ссылок."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger("app")


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
