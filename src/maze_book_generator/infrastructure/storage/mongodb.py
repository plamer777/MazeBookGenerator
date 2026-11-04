"""Подключение к MongoDB: lifecycle соединения без запросной логики.

Запросная логика хранилища тем находится в
``theme_repository.MongoThemeRepository`` — клиент отвечает только
за ленивое создание ``MongoClient`` и доступ к коллекции.
"""

from typing import Any

from pymongo import MongoClient

from maze_book_generator.settings import settings


class MongoDBClient:
    """Управляет соединением с MongoDB: ленивое создание, коллекция, close."""

    def __init__(self) -> None:
        """Инициализация клиента с настройками из settings."""
        self._client: MongoClient | None = None
        self._db_name = settings.MONGODB_DB_NAME
        self._collection_name = settings.MONGODB_COLLECTION_THEMES

    @property
    def collection(self) -> Any:
        """Возвращает коллекцию used_themes (соединение создаётся лениво)."""
        if self._client is None:
            self._client = MongoClient(settings.MONGODB_URI)
        return self._client[self._db_name][self._collection_name]

    def close(self) -> None:
        """Закрывает соединение с MongoDB."""
        if self._client is not None:
            self._client.close()
            self._client = None
