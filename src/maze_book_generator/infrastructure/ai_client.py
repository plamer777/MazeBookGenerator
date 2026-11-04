"""Клиент для AI API генерации тем."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from openai import APIError, AsyncOpenAI

from maze_book_generator.domain.models import PagePrompt, Theme
from maze_book_generator.localization import BookTexts, Language
from maze_book_generator.settings import (
    AI_THEME_ATTEMPTS,
    AI_THEME_MAX_TOKENS_BASE,
    AI_THEME_MAX_TOKENS_PER_PAGE,
    AI_THEME_RETRY_DELAY,
    OPEN_AI_THEME_MODEL,
    OPEN_AI_THEME_PROMPT,
    OPEN_AI_THEME_PROMPT_RU,
    OPEN_AI_THEME_SYSTEM,
    OPEN_AI_THEME_SYSTEM_RU,
    OPEN_AI_THEME_TEMPERATURE,
    settings,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThemeHints:
    """Опциональные подсказки для генерации темы книги."""

    book_title_hint: str | None = None
    theme_hint: str | None = None
    age_range: str | None = None
    print_friendly: bool = False


class AIClient:
    """Клиент для взаимодействия с OpenAI API для генерации тем книг."""

    def __init__(self) -> None:
        """Инициализация клиента с ключом из settings."""
        self._client: AsyncOpenAI | None = (
            AsyncOpenAI(api_key=settings.OPEN_AI_KEY) if settings.OPEN_AI_KEY else None
        )

    async def generate_theme(
        self,
        pages_count: int,
        used_titles: list[str] | None = None,
        language: Language = "en",
        hints: ThemeHints | None = None,
    ) -> Theme:
        """
        Генерирует тему книги через OpenAI.

        Args:
            pages_count: Количество страниц в книге
            used_titles: Список уже использованных названий для исключения повторений
            language: Язык генерируемого контента ('en' или 'ru')
            hints: Опциональные подсказки темы (название, тематика, возраст, print_friendly)

        Returns:
            Объект Theme с заголовком, заданиями и ключевыми словами
        """
        if self._client is None:
            msg = "OpenAI client is not initialized"
            raise ValueError(msg)

        system_prompt = OPEN_AI_THEME_SYSTEM if language == "en" else OPEN_AI_THEME_SYSTEM_RU
        gen_prompt = self._prepare_theme_generate_prompt(used_titles, language, pages_count, hints)

        last_error = ""
        for _ in range(AI_THEME_ATTEMPTS):
            try:
                # Увеличенный бюджет токенов для структурированного маркетплейс-описания.
                max_tokens = AI_THEME_MAX_TOKENS_BASE + pages_count * AI_THEME_MAX_TOKENS_PER_PAGE
                response = await self._client.chat.completions.create(
                    model=OPEN_AI_THEME_MODEL,
                    temperature=OPEN_AI_THEME_TEMPERATURE,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": gen_prompt},
                    ],
                )
                text = response.choices[0].message.content or ""
                
                parsed = self._parse_theme_response(text, pages_count, language)
                if parsed is not None:
                    return parsed

                last_error = "response could not be parsed"
                await asyncio.sleep(AI_THEME_RETRY_DELAY)

            except APIError as exc:
                last_error = str(exc)
                logger.warning("Failed to generate theme: %s", exc)

        msg = f"Failed to generate theme after {AI_THEME_ATTEMPTS} attempts"
        if last_error:
            msg += f": {last_error}"
        raise ValueError(msg)

    def _prepare_theme_generate_prompt(
        self,
        used_titles: list[str] | None,
        language: Language,
        pages_count: int,
        hints: ThemeHints | None,
    ) -> str:
        """Подготавливает промпт генерации темы текущей книги."""
        hints = hints or ThemeHints()
        titles_block = (
            "\n".join(f"- {t}" for t in used_titles)
            if used_titles
            else ("none yet" if language == "en" else "пока нет")
        )

        prompt_tpl = OPEN_AI_THEME_PROMPT if language == "en" else OPEN_AI_THEME_PROMPT_RU
        language_name = "Russian" if language == "ru" else "English"
        return prompt_tpl.format(
            pages_count=pages_count,
            used_titles=titles_block,
            language_name=language_name,
            book_title_hint=self._safe_prompt_value(hints.book_title_hint or "auto"),
            theme_hint=self._safe_prompt_value(hints.theme_hint or "auto"),
            age_range=self._safe_prompt_value(hints.age_range or ("4-7 years" if language == "en" else "4-7 лет")),
            answers_included=("yes" if language == "en" else "да"),
            print_friendly=(
                "yes" if language == "en" and hints.print_friendly else
                "no" if language == "en" else
                "да" if hints.print_friendly else
                "нет"
            ),
        )

    @staticmethod
    def _safe_prompt_value(value: str) -> str:
        """Экранирует фигурные скобки, чтобы не ломать format-шаблон."""
        return value.replace("{", "(").replace("}", ")")

    def _parse_theme_response(self, raw: str, pages_count: int, language: Language = "en") -> Theme | None:
        """
        Парсит JSON-ответ OpenAI в структуру Theme.

        Args:
            raw: Сырой текст из ответа модели
            pages_count: Количество страниц (для валидации)
            language: Язык текстов темы ('en' или 'ru')

        Returns:
            Theme или None при ошибке парсинга
        """
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            return None

        try:
            payload: dict[str, Any] = json.loads(cleaned[start:end])
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None

        t = BookTexts(language)

        raw_prompts: list[Any] = payload.get("page_prompts", [])
        prompts: list[PagePrompt] = [
            PagePrompt(
                task=item.get("task", t.get("fallback_maze_task")),
                heroes=item.get("heroes", []),
            )
            for item in raw_prompts
            if isinstance(item, dict)
        ]
        while len(prompts) < pages_count:
            n = len(prompts) + 1
            prompts.append(PagePrompt(
                task=t.get("fallback_maze_task_n").format(n=n),
                heroes=[],
            ))

        keywords: list[list[str]] = payload.get("image_keywords", [])
        while len(keywords) < pages_count:
            keywords.append(t.get("fallback_keywords").split(","))

        book_title = payload.get("book_title", t.get("fallback_book_title"))
        book_description = payload.get("book_description", t.get("fallback_book_description"))
        marketplace_title = payload.get("marketplace_title") or book_title
        marketplace_description = payload.get("marketplace_description") or book_description

        return Theme(
            book_title=book_title,
            book_description=book_description,
            page_prompts=prompts,
            image_notes=payload.get("image_notes"),
            image_keywords=keywords,
            marketplace_title=marketplace_title,
            marketplace_description=marketplace_description,
        )
