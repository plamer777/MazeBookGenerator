"""Клиент для AI API генерации тем."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from src.domain.models import PagePrompt, Theme
from src.localization import BookTexts, Language
from src.settings import (
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
        prompt = prompt_tpl.format(pages_count=pages_count, used_titles=titles_block)

        for _ in range(3):
            try:
                # ~50 токенов на страницу + 300 на заголовок/описание/структуру JSON
                max_tokens = 300 + pages_count * 50
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
        prompts: list[PagePrompt] = []
        for item in raw_prompts:
            if isinstance(item, dict):
                prompts.append(PagePrompt(
                    task=item.get("task", t.get("fallback_maze_task")),
                    heroes=item.get("heroes", []),
                ))
        while len(prompts) < pages_count:
            n = len(prompts) + 1
            prompts.append(PagePrompt(
                task=t.get("fallback_maze_task_n").replace("{n}", str(n)),
                heroes=[],
            ))

        keywords: list[list[str]] = payload.get("image_keywords", [])
        while len(keywords) < pages_count:
            keywords.append(t.get("fallback_keywords").split(","))

        return Theme(
            book_title=payload.get("book_title", t.get("fallback_book_title")),
            book_description=payload.get("book_description", t.get("fallback_book_description")),
            page_prompts=prompts,
            image_notes=payload.get("image_notes"),
            image_keywords=keywords,
        )
