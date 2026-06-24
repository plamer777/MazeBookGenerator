"""Контейнер зависимостей для MazeBookGenerator."""

from src.domain.maze_generator import MazeGenerator
from src.infrastructure.ai_client import AIClient
from src.infrastructure.hf_client import HFClient
from src.infrastructure.image_generator import ImageGenerator
from src.infrastructure.mongodb_client import MongoDBClient
from src.infrastructure.pdf_renderer import PDFRenderer
from src.infrastructure.preview_generator import PreviewGenerator


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


container = Container()

