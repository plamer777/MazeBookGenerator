"""Клиент для AI API генерации тем."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from src.domain.models import PagePrompt, Theme
from src.settings import (
    OPEN_AI_THEME_MODEL,
    OPEN_AI_THEME_PROMPT,
    OPEN_AI_THEME_SYSTEM,
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

    async def generate_theme(self, pages_count: int, used_titles: list[str] | None = None) -> Theme:
        """
        Генерирует тему книги через OpenAI.

        Args:
            pages_count: Количество страниц в книге
            used_titles: Список уже использованных названий для исключения повторений

        Returns:
            Объект Theme с заголовком, заданиями и ключевыми словами
        """
        if self._client is None:
            raise ValueError("OpenAI client is not initialized")

        titles_block = (
            "\n".join(f"- {t}" for t in used_titles)
            if used_titles
            else "none yet"
        )
        prompt = OPEN_AI_THEME_PROMPT.format(pages_count=pages_count, used_titles=titles_block)

        for _ in range(3):
            try:
                response = await self._client.chat.completions.create(
                    model=OPEN_AI_THEME_MODEL,
                    temperature=OPEN_AI_THEME_TEMPERATURE,
                    max_tokens=700,
                    messages=[
                        {"role": "system", "content": OPEN_AI_THEME_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                )
                text = response.choices[0].message.content or ""
                parsed = self._parse_theme_response(text, pages_count)
                if parsed is not None:
                    return parsed
                await asyncio.sleep(1)

            except Exception:
                pass

        raise ValueError("Failed to generate theme after 3 attempts")

    def _parse_theme_response(self, raw: str, pages_count: int) -> Theme | None:
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

        raw_prompts: list[Any] = payload.get("page_prompts", [])
        prompts: list[PagePrompt] = []
        for item in raw_prompts:
            if isinstance(item, dict):
                prompts.append(PagePrompt(
                    task=item.get("task", "Find the path through the maze"),
                    heroes=item.get("heroes", []),
                ))
        while len(prompts) < pages_count:
            prompts.append(PagePrompt(task=f"Find the path through maze #{len(prompts) + 1}", heroes=[]))

        keywords: list[list[str]] = payload.get("image_keywords", [])
        while len(keywords) < pages_count:
            keywords.append(["maze", "adventure"])

        return Theme(
            book_title=payload.get("book_title", "Maze Adventure"),
            book_description=payload.get("book_description", "An exciting maze adventure."),
            page_prompts=prompts,
            image_notes=payload.get("image_notes"),
            image_keywords=keywords,
        )
