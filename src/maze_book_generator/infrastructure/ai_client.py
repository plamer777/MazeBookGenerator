"""Клиент для AI API генерации тем."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from maze_book_generator.domain.models import PagePrompt, Theme
from maze_book_generator.localization import BookTexts, Language
from maze_book_generator.settings import (
    OPEN_AI_THEME_MODEL,
    OPEN_AI_THEME_PROMPT,
    OPEN_AI_THEME_PROMPT_RU,
    OPEN_AI_THEME_SYSTEM,
    OPEN_AI_THEME_SYSTEM_RU,
    OPEN_AI_THEME_TEMPERATURE,
    settings,
)


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
        book_title_hint: str | None = None,
        theme_hint: str | None = None,
        age_range: str | None = None,
        print_friendly: bool = False,
    ) -> Theme:
        """
        Генерирует тему книги через OpenAI.

        Args:
            pages_count: Количество страниц в книге
            used_titles: Список уже использованных названий для исключения повторений
            language: Язык генерируемого контента ('en' или 'ru')

        Returns:
            Объект Theme с заголовком, заданиями и ключевыми словами
        """
        if self._client is None:
            raise ValueError("OpenAI client is not initialized")

        titles_block = (
            "\n".join(f"- {t}" for t in used_titles)
            if used_titles
            else ("none yet" if language == "en" else "пока нет")
        )

        system = OPEN_AI_THEME_SYSTEM if language == "en" else OPEN_AI_THEME_SYSTEM_RU
        prompt_tpl = OPEN_AI_THEME_PROMPT if language == "en" else OPEN_AI_THEME_PROMPT_RU
        language_name = "Russian" if language == "ru" else "English"
        prompt = prompt_tpl.format(
            pages_count=pages_count,
            used_titles=titles_block,
            language_name=language_name,
            book_title_hint=self._safe_prompt_value(book_title_hint or "auto"),
            theme_hint=self._safe_prompt_value(theme_hint or "auto"),
            age_range=self._safe_prompt_value(age_range or ("4-7 years" if language == "en" else "4-7 лет")),
            answers_included=("yes" if language == "en" else "да"),
            print_friendly=(
                "yes" if language == "en" and print_friendly else
                "no" if language == "en" else
                "да" if print_friendly else
                "нет"
            ),
        )

        for _ in range(3):
            try:
                # Увеличенный бюджет токенов для структурированного маркетплейс-описания.
                max_tokens = 500 + pages_count * 60
                response = await self._client.chat.completions.create(
                    model=OPEN_AI_THEME_MODEL,
                    temperature=OPEN_AI_THEME_TEMPERATURE,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                )
                text = response.choices[0].message.content or ""
                
                parsed = self._parse_theme_response(text, pages_count, language)
                if parsed is not None:
                    return parsed

                await asyncio.sleep(1)

            except Exception as e:
                print(f'Failed to generate theme: {e}')

        raise ValueError("Failed to generate theme after 3 attempts")

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
