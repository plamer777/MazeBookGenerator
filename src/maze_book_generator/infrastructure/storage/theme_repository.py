"""Репозиторий использованных тем книг: JSON-файл или MongoDB.

По умолчанию приложение не требует внешних сервисов — темы хранятся
в ``output/used_themes.json`` (JsonThemeRepository). MongoThemeRepository
включается настройкой ``MONGODB_ENABLED=true``.
"""

from __future__ import annotations

import json
import logging
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class ThemeRepository(Protocol):
    """Хранилище заголовков уже сгенерированных книг (дедупликация тем)."""

    def is_theme_used(self, title: str) -> bool:
        """Возвращает True, если тема с таким заголовком уже использовалась."""
        ...

    def save_theme(self, title: str) -> None:
        """Сохраняет заголовок темы как использованный."""
        ...

    def get_used_titles(self) -> list[str]:
        """Возвращает список всех использованных заголовков."""
        ...

    def get_used_themes_count(self) -> int:
        """Возвращает количество сохранённых тем."""
        ...

    def close(self) -> None:
        """Освобождает ресурсы хранилища (для JSON — no-op)."""
        ...


class JsonThemeRepository:
    """Репозиторий тем на основе JSON-файла (дефолтное хранилище)."""

    def __init__(self, path: Path) -> None:
        """
        Инициализация репозитория.

        Args:
            path: Путь к JSON-файлу (родительские директории создаются лениво)
        """
        self._path = path

    def _load_records(self) -> list[dict[str, Any]]:
        """Читает записи из файла; повреждённый/отсутствующий файл = пустой список."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Не удалось прочитать %s: %s", self._path, exc)
            return []
        return data if isinstance(data, list) else []

    def _save_records(self, records: list[dict[str, Any]]) -> None:
        """Атомарно записывает записи (через временный файл)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp_path.replace(self._path)

    def is_theme_used(self, title: str) -> bool:
        """Возвращает True, если тема с таким заголовком уже использовалась."""
        return any(record.get("title") == title for record in self._load_records())

    def save_theme(self, title: str) -> None:
        """Добавляет заголовок темы с меткой времени."""
        try:
            records = self._load_records()
            records.append({"title": title, "timestamp": datetime.now(UTC).isoformat()})
            self._save_records(records)
        except OSError as exc:
            logger.warning("Не удалось сохранить тему в %s: %s", self._path, exc)

    def get_used_titles(self) -> list[str]:
        """Возвращает список всех использованных заголовков."""
        return [r["title"] for r in self._load_records() if "title" in r]

    def get_used_themes_count(self) -> int:
        """Возвращает количество сохранённых тем."""
        return len(self._load_records())

    def close(self) -> None:
        """No-op: JSON-хранилище не держит открытых ресурсов."""


def _pymongo_errors() -> tuple[type[Exception], ...]:
    """Возвращает ошибки pymongo (импорт ленивый — pymongo опциональная зависимость)."""
    from pymongo.errors import PyMongoError

    return (PyMongoError,)


class MongoThemeRepository:
    """Репозиторий тем поверх MongoDB: запросная логика к used_themes.

    Соединение управляется MongoDBClient и создаётся лениво — pymongo
    требуется только при первом реальном вызове. При недоступности
    MongoDB методы деградируют к безопасным значениям, не прерывая работу.
    """

    def __init__(self) -> None:
        """Создаёт репозиторий без соединения (MongoDBClient — ленивый)."""
        self._client: Any | None = None

    @property
    def _collection(self) -> Any:
        """Возвращает коллекцию тем, создавая клиент при первом обращении."""
        if self._client is None:
            from maze_book_generator.infrastructure.storage.mongodb import (
                MongoDBClient,
            )

            self._client = MongoDBClient()
        return self._client.collection

    def is_theme_used(self, title: str) -> bool:
        """Возвращает True, если тема с таким заголовком уже использовалась."""
        try:
            return self._collection.find_one({"title": title}) is not None
        except _pymongo_errors():
            return False

    def save_theme(self, title: str) -> None:
        """Сохраняет заголовок темы как использованный."""
        with suppress(*_pymongo_errors()):
            self._collection.insert_one({"title": title, "timestamp": datetime.now(UTC)})

    def get_used_titles(self) -> list[str]:
        """Возвращает список всех использованных заголовков."""
        try:
            return [doc["title"] for doc in self._collection.find({}, {"title": 1})]
        except _pymongo_errors():
            return []

    def get_used_themes_count(self) -> int:
        """Возвращает количество сохранённых тем."""
        try:
            return self._collection.count_documents({})
        except _pymongo_errors():
            return 0

    def close(self) -> None:
        """Закрывает соединение с MongoDB, если оно было открыто."""
        if self._client is not None:
            self._client.close()
            self._client = None
