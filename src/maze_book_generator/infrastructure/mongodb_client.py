"""Клиент для MongoDB хранения использованных тем."""

from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

from maze_book_generator.settings import settings


class MongoDBClient:
    """Клиент для взаимодействия с MongoDB."""

    def __init__(self) -> None:
        """Инициализация клиента с настройками из settings."""
        self._client: MongoClient | None = None
        self._db_name = settings.MONGODB_DB_NAME
        self._collection_name = settings.MONGODB_COLLECTION_THEMES

    @property
    def client(self) -> MongoClient:
        """Получает экземпляр клиента MongoDB (lazy initialization)."""
        if self._client is None:
            self._client = MongoClient(settings.MONGODB_URI)
        return self._client

    @property
    def collection(self) -> Any:
        """Получает коллекцию used_themes."""
        return self.client[self._db_name][self._collection_name]

    def is_theme_used(self, title: str) -> bool:
        """
        Проверяет, использовалась ли тема ранее.

        Args:
            title: Название темы

        Returns:
            True если тема уже использовалась, иначе False
        """
        try:
            result = self.collection.find_one({"title": title})
        except (ConnectionFailure, PyMongoError):
            # Если MongoDB недоступен, возвращаем False (позволяем продолжить)
            return False
        return result is not None

    def save_theme(self, title: str) -> None:
        """
        Сохраняет тему как использованную.

        Args:
            title: Название темы
        """
        # Если MongoDB недоступен, игнорируем ошибку сохранения
        with suppress(ConnectionFailure, PyMongoError):
            self.collection.insert_one(
                {
                    "title": title,
                    "timestamp": datetime.now(UTC),
                }
            )

    def get_used_titles(self) -> list[str]:
        """
        Возвращает список названий всех использованных тем.

        Returns:
            Список строк-заголовков
        """
        try:
            return [doc["title"] for doc in self.collection.find({}, {"title": 1})]
        except (ConnectionFailure, PyMongoError):
            return []

    def get_used_themes_count(self) -> int:
        """
        Получает количество использованных тем.

        Returns:
            Количество тем в коллекции
        """
        try:
            return self.collection.count_documents({})
        except (ConnectionFailure, PyMongoError):
            return 0

    def close(self) -> None:
        """Закрывает соединение с MongoDB."""
        if self._client is not None:
            self._client.close()
            self._client = None
