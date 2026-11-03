"""Тесты DI-контейнера: ленивая инициализация и кэширование зависимостей."""

from maze_book_generator.container import Container


class TestContainer:
    """Проверяет, что контейнер лениво создаёт и кэширует зависимости."""

    def test_properties_create_instances_lazily(self) -> None:
        """Каждое property должно создавать экземпляр при первом обращении."""
        container = Container()

        assert container._maze_generator is None
        generator = container.maze_generator

        assert generator is container._maze_generator

    def test_properties_return_cached_instances(self) -> None:
        """Повторное обращение должно возвращать тот же объект."""
        container = Container()

        assert container.maze_generator is container.maze_generator
        assert container.pdf_renderer is container.pdf_renderer
        assert container.ai_client is container.ai_client
        assert container.mongodb_client is container.mongodb_client
        assert container.image_generator is container.image_generator
        assert container.preview_generator is container.preview_generator
        assert container.hf_client is container.hf_client
        assert container.pollinations_client is container.pollinations_client
        assert container.replicate_client is container.replicate_client
