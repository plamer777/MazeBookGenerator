"""Unit-тесты для AIClient с моками OpenAI."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import APIError

from maze_book_generator.infrastructure.ai_client import AIClient


def _api_error(msg: str) -> APIError:
    """Создаёт APIError для имитации сбоя OpenAI в тестах."""
    return APIError(msg, request=httpx.Request("POST", "https://api.test"), body=None)


class TestAIClient:
    """Проверяет логику клиента OpenAI с моками."""

    def setup_method(self) -> None:
        """Инициализация клиента."""
        self.client = AIClient()

    def test_initialization_with_key(self) -> None:
        """Инициализация с ключом должна создавать AsyncOpenAI клиент."""
        with patch("maze_book_generator.infrastructure.ai_client.settings") as mock_settings:
            mock_settings.OPEN_AI_KEY = "test-key"
            client = AIClient()
            assert client._client is not None

    def test_initialization_without_key(self) -> None:
        """Инициализация без ключа должна создавать None клиент."""
        with patch("maze_book_generator.infrastructure.ai_client.settings") as mock_settings:
            mock_settings.OPEN_AI_KEY = None
            client = AIClient()
            assert client._client is None

    def test_safe_prompt_value_escapes_braces(self) -> None:
        """Экранирование фигурных скобок."""
        assert AIClient._safe_prompt_value("test{value}") == "test(value)"
        assert AIClient._safe_prompt_value("test}value{") == "test)value("
        assert AIClient._safe_prompt_value("no_braces") == "no_braces"

class TestAIClientParse:
    """Набор тестов."""

    def setup_method(self) -> None:
        """Инициализация клиента."""
        self.client = AIClient()


    def test_parse_theme_response_valid_json(self) -> None:
        """Парсинг валидного JSON ответа."""
        raw = json.dumps({
            "book_title": "Test Title",
            "book_description": "Test Description",
            "page_prompts": [
                {"task": "Task 1", "heroes": ["hero1"]},
                {"task": "Task 2", "heroes": ["hero2"]},
            ],
            "image_keywords": [["key1", "key2"], ["key3", "key4"]],
            "marketplace_title": "Marketplace Title",
            "marketplace_description": "Marketplace Description",
        })

        theme = self.client._parse_theme_response(raw, 2, "en")
        assert theme is not None
        assert theme.book_title == "Test Title"
        assert theme.book_description == "Test Description"
        assert len(theme.page_prompts) == 2
        assert theme.page_prompts[0].task == "Task 1"
        assert theme.marketplace_title == "Marketplace Title"

    def test_parse_theme_response_with_json_prefix(self) -> None:
        """Парсинг JSON с префиксом ```json."""
        raw = "```json\n" + json.dumps({
            "book_title": "Test Title",
            "book_description": "Test Description",
            "page_prompts": [{"task": "Task 1", "heroes": []}],
            "image_keywords": [["key1"]],
        }) + "\n```"

        theme = self.client._parse_theme_response(raw, 1, "en")
        assert theme is not None
        assert theme.book_title == "Test Title"

    def test_parse_theme_response_with_extra_text(self) -> None:
        """Парсинг JSON с дополнительным текстом."""
        raw = "Some text before\n" + json.dumps({
            "book_title": "Test Title",
            "book_description": "Test Description",
            "page_prompts": [{"task": "Task 1", "heroes": []}],
            "image_keywords": [["key1"]],
        }) + "\nSome text after"

        theme = self.client._parse_theme_response(raw, 1, "en")
        assert theme is not None
        assert theme.book_title == "Test Title"

    def test_parse_theme_response_invalid_json(self) -> None:
        """Парсинг невалидного JSON должен возвращать None."""
        raw = "not a json"
        theme = self.client._parse_theme_response(raw, 1, "en")
        assert theme is None

    def test_parse_theme_response_no_json_object(self) -> None:
        """Отсутствие JSON объекта должно возвращать None."""
        raw = "some text without braces"
        theme = self.client._parse_theme_response(raw, 1, "en")
        assert theme is None

    def test_parse_theme_response_fills_missing_prompts(self) -> None:
        """Заполнение недостающих промптов fallback значениями."""
        raw = json.dumps({
            "book_title": "Test Title",
            "book_description": "Test Description",
            "page_prompts": [{"task": "Task 1", "heroes": []}],
            "image_keywords": [["key1"]],
        })

        theme = self.client._parse_theme_response(raw, 3, "en")
        assert len(theme.page_prompts) == 3
        assert theme.page_prompts[0].task == "Task 1"
        assert "maze" in theme.page_prompts[1].task.lower()
        assert "maze" in theme.page_prompts[2].task.lower()

    def test_parse_theme_response_fills_missing_keywords(self) -> None:
        """Заполнение недостающих keywords fallback значениями."""
        raw = json.dumps({
            "book_title": "Test Title",
            "book_description": "Test Description",
            "page_prompts": [{"task": "Task 1", "heroes": []}],
            "image_keywords": [["key1"]],
        })

        theme = self.client._parse_theme_response(raw, 3, "en")
        assert len(theme.image_keywords) == 3
        assert theme.image_keywords[0] == ["key1"]
        assert theme.image_keywords[1] == ["maze", "adventure"]
        assert theme.image_keywords[2] == ["maze", "adventure"]

    def test_parse_theme_response_fallback_title_description(self) -> None:
        """Fallback для title и description при отсутствии."""
        raw = json.dumps({
            "page_prompts": [{"task": "Task 1", "heroes": []}],
            "image_keywords": [["key1"]],
        })

        theme = self.client._parse_theme_response(raw, 1, "en")
        assert theme.book_title is not None
        assert theme.book_description is not None

    def test_parse_theme_response_marketplace_fallback(self) -> None:
        """Fallback для marketplace полей к базовым."""
        raw = json.dumps({
            "book_title": "Test Title",
            "book_description": "Test Description",
            "page_prompts": [{"task": "Task 1", "heroes": []}],
            "image_keywords": [["key1"]],
        })

        theme = self.client._parse_theme_response(raw, 1, "en")
        assert theme.marketplace_title == "Test Title"
        assert theme.marketplace_description == "Test Description"

    def test_parse_theme_response_empty_prompts_list(self) -> None:
        """Обработка пустого списка промптов."""
        raw = json.dumps({
            "book_title": "Test Title",
            "book_description": "Test Description",
            "page_prompts": [],
            "image_keywords": [],
        })

        theme = self.client._parse_theme_response(raw, 2, "en")
        assert len(theme.page_prompts) == 2
        assert len(theme.image_keywords) == 2

    def test_parse_theme_response_malformed_prompt_item(self) -> None:
        """Обработка некорректного элемента в page_prompts."""
        raw = json.dumps({
            "book_title": "Test Title",
            "book_description": "Test Description",
            "page_prompts": ["not a dict", {"task": "Task 1", "heroes": []}],
            "image_keywords": [["key1"], ["key2"]],
        })

        theme = self.client._parse_theme_response(raw, 2, "en")
        assert len(theme.page_prompts) == 2
        # Первый элемент (строка) пропускается, второй валидный
        assert theme.page_prompts[0].task == "Task 1"
        # Третий элемент заполняется fallback
        assert "maze" in theme.page_prompts[1].task.lower()

class TestAIClientGenerate:
    """Набор тестов."""

    def setup_method(self) -> None:
        """Инициализация клиента."""
        self.client = AIClient()


    async def test_generate_theme_with_mock_openai(self) -> None:
        """Генерация темы с моком OpenAI."""
        with patch("maze_book_generator.infrastructure.ai_client.settings") as mock_settings:
            mock_settings.OPEN_AI_KEY = "test-key"
            client = AIClient()

            # Мокаем OpenAI клиент
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "book_title": "AI Title",
                "book_description": "AI Description",
                "page_prompts": [
                    {"task": "AI Task 1", "heroes": ["hero1"]},
                    {"task": "AI Task 2", "heroes": ["hero2"]},
                ],
                "image_keywords": [["key1"], ["key2"]],
            })

            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
            client._client = mock_openai

            theme = await client.generate_theme(
                pages_count=2,
                used_titles=["Old Title"],
                language="en",
            )

            assert theme.book_title == "AI Title"
            assert len(theme.page_prompts) == 2

    async def test_generate_theme_without_client_raises(self) -> None:
        """Генерация без клиента должна вызывать ValueError."""
        with patch("maze_book_generator.infrastructure.ai_client.settings") as mock_settings:
            mock_settings.OPEN_AI_KEY = None
            client = AIClient()

            with pytest.raises(ValueError, match="not initialized"):
                await client.generate_theme(pages_count=2, language="en")

    async def test_generate_theme_retry_on_failure(self) -> None:
        """Повторные попытки при ошибке OpenAI."""
        with patch("maze_book_generator.infrastructure.ai_client.settings") as mock_settings:
            mock_settings.OPEN_AI_KEY = "test-key"
            client = AIClient()

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "book_title": "AI Title",
                "book_description": "AI Description",
                "page_prompts": [{"task": "Task 1", "heroes": []}],
                "image_keywords": [["key1"]],
            })

            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(
                side_effect=[_api_error("Error 1"), _api_error("Error 2"), mock_response]
            )
            client._client = mock_openai

            theme = await client.generate_theme(pages_count=1, language="en")

            assert theme.book_title == "AI Title"
            assert mock_openai.chat.completions.create.call_count == 3

    async def test_generate_theme_fails_after_max_retries(self) -> None:
        """Ошибка после максимального количества попыток."""
        with patch("maze_book_generator.infrastructure.ai_client.settings") as mock_settings:
            mock_settings.OPEN_AI_KEY = "test-key"
            client = AIClient()

            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(
                side_effect=_api_error("Always fails")
            )
            client._client = mock_openai

            with pytest.raises(ValueError, match="Failed to generate"):
                await client.generate_theme(pages_count=1, language="en")

    def test_parse_theme_response_russian_language(self) -> None:
        """Парсинг с русским языком для fallback значений."""
        raw = json.dumps({
            "book_title": "Тест",
            "book_description": "Описание",
            "page_prompts": [],
            "image_keywords": [],
        })

        theme = self.client._parse_theme_response(raw, 1, "ru")
        assert theme is not None
        # Fallback промпт должен быть на русском
        assert "лабиринт" in theme.page_prompts[0].task.lower()
