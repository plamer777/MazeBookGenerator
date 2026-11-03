"""Контейнер зависимостей для MazeBookGenerator."""

from __future__ import annotations

import logging
from importlib.util import find_spec

from maze_book_generator.domain.maze import MazeGenerator
from maze_book_generator.infrastructure.ai_client import AIClient
from maze_book_generator.infrastructure.images.hf import HFClient
from maze_book_generator.infrastructure.images.pollinations import PollinationsClient
from maze_book_generator.infrastructure.images.replicate import ReplicateClient
from maze_book_generator.infrastructure.preview_generator import PreviewGenerator
from maze_book_generator.infrastructure.storage.theme_repository import (
    JsonThemeRepository,
    ThemeRepository,
)
from maze_book_generator.settings import USED_THEMES_FILENAME, settings

logger = logging.getLogger(__name__)


class Container:
    """Контейнер для управления зависимостями приложения."""

    def __init__(self) -> None:
        """Инициализация контейнера с компонентами."""
        self._maze_generator: MazeGenerator | None = None
        self._ai_client: AIClient | None = None
        self._theme_repository: ThemeRepository | None = None
        self._preview_generator: PreviewGenerator | None = None
        self._hf_client: HFClient | None = None
        self._pollinations_client: PollinationsClient | None = None
        self._replicate_client: ReplicateClient | None = None

    @property
    def maze_generator(self) -> MazeGenerator:
        """Получает экземпляр генератора лабиринтов."""
        if self._maze_generator is None:
            self._maze_generator = MazeGenerator()
        return self._maze_generator

    @property
    def ai_client(self) -> AIClient:
        """Получает экземпляр AI клиента."""
        if self._ai_client is None:
            self._ai_client = AIClient()
        return self._ai_client

    @property
    def theme_repository(self) -> ThemeRepository:
        """
        Получает репозиторий использованных тем.

        По умолчанию — JSON-файл в OUTPUT_DIR. При MONGODB_ENABLED=true
        и установленном pymongo — MongoDB-хранилище.
        """
        if self._theme_repository is None:
            self._theme_repository = self._create_theme_repository()
        return self._theme_repository

    def _create_theme_repository(self) -> ThemeRepository:
        """Выбирает бэкенд репозитория по настройкам и доступности pymongo."""
        if settings.MONGODB_ENABLED:
            if find_spec("pymongo") is not None:
                from maze_book_generator.infrastructure.storage.theme_repository import (
                    MongoThemeRepository,
                )

                return MongoThemeRepository()
            logger.warning(
                "MONGODB_ENABLED=true, но pymongo не установлен — "
                "используется JSON-хранилище тем"
            )
        return JsonThemeRepository(settings.OUTPUT_DIR / USED_THEMES_FILENAME)

    @property
    def preview_generator(self) -> PreviewGenerator:
        """Получает экземпляр генератора preview."""
        if self._preview_generator is None:
            self._preview_generator = PreviewGenerator()
        return self._preview_generator

    @property
    def hf_client(self) -> HFClient:
        """Получает экземпляр Hugging Face клиента."""
        if self._hf_client is None:
            self._hf_client = HFClient()
        return self._hf_client

    @property
    def pollinations_client(self) -> PollinationsClient:
        """Получает экземпляр Pollinations клиента."""
        if self._pollinations_client is None:
            self._pollinations_client = PollinationsClient()
        return self._pollinations_client

    @property
    def replicate_client(self) -> ReplicateClient:
        """Получает экземпляр Replicate клиента."""
        if self._replicate_client is None:
            self._replicate_client = ReplicateClient()
        return self._replicate_client


container = Container()
