"""Контейнер зависимостей для MazeBookGenerator."""

from maze_book_generator.domain.maze_generator import MazeGenerator
from maze_book_generator.infrastructure.ai_client import AIClient
from maze_book_generator.infrastructure.hf_client import HFClient
from maze_book_generator.infrastructure.image_generator import ImageGenerator
from maze_book_generator.infrastructure.mongodb_client import MongoDBClient
from maze_book_generator.infrastructure.pdf_renderer import PDFRenderer
from maze_book_generator.infrastructure.pollinations_client import PollinationsClient
from maze_book_generator.infrastructure.preview_generator import PreviewGenerator
from maze_book_generator.infrastructure.replicate_client import ReplicateClient


class Container:
    """Контейнер для управления зависимостями приложения."""

    def __init__(self) -> None:
        """Инициализация контейнера с компонентами."""
        self._maze_generator: MazeGenerator | None = None
        self._pdf_renderer: PDFRenderer | None = None
        self._ai_client: AIClient | None = None
        self._mongodb_client: MongoDBClient | None = None
        self._image_generator: ImageGenerator | None = None
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
    def pdf_renderer(self) -> PDFRenderer:
        """Получает экземпляр PDF рендерера."""
        if self._pdf_renderer is None:
            self._pdf_renderer = PDFRenderer()
        return self._pdf_renderer

    @property
    def ai_client(self) -> AIClient:
        """Получает экземпляр AI клиента."""
        if self._ai_client is None:
            self._ai_client = AIClient()
        return self._ai_client

    @property
    def mongodb_client(self) -> MongoDBClient:
        """Получает экземпляр MongoDB клиента."""
        if self._mongodb_client is None:
            self._mongodb_client = MongoDBClient()
        return self._mongodb_client

    @property
    def image_generator(self) -> ImageGenerator:
        """Получает экземпляр генератора изображений."""
        if self._image_generator is None:
            self._image_generator = ImageGenerator()
        return self._image_generator

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

