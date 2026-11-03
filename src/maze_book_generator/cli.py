"""CLI-интерфейс MazeBookGenerator.

Примеры:
    mazebook generate
    mazebook generate --books 3 --pages 20 --size 17x13 --preset en_school
    mazebook generate --difficulty CHALLENGE_HARD --seed 42 --no-images
"""

import argparse
import asyncio
from dataclasses import replace

from maze_book_generator.application.book_factory import (
    BookSpec,
    build_default_theme,
)
from maze_book_generator.application.book_service import BookService
from maze_book_generator.application.config_presets import PRESETS, personalized
from maze_book_generator.container import container
from maze_book_generator.domain.models import BookConfig, DifficultyMode


def _parse_size(value: str) -> tuple[int, int]:
    """Парсит размер лабиринта в формате WxH (например, 15x11)."""
    try:
        width, height = value.lower().split("x")
        return int(width), int(height)
    except ValueError as exc:
        msg = f"размер должен быть вида 15x11, получено: {value}"
        raise argparse.ArgumentTypeError(msg) from exc


def build_parser() -> argparse.ArgumentParser:
    """Собирает argparse-парсер CLI."""
    parser = argparse.ArgumentParser(
        prog="mazebook",
        description="Генератор книг лабиринтов с PDF, иллюстрациями и превью",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="сгенерировать книги лабиринтов")
    gen.add_argument("--books", type=int, default=1, help="количество книг (по умолчанию 1)")
    gen.add_argument("--pages", type=int, default=30, help="лабиринтов в книге (по умолчанию 30)")
    gen.add_argument(
        "--size", type=_parse_size, default=(15, 11),
        help="размер лабиринта WxH (по умолчанию 15x11)",
    )
    gen.add_argument(
        "--preset", choices=sorted(PRESETS), default="ru_kids_easy",
        help="пресет BookConfig (по умолчанию ru_kids_easy)",
    )
    gen.add_argument(
        "--difficulty",
        choices=[mode.name for mode in DifficultyMode],
        default=DifficultyMode.KIDS_EASY.name,
        help="режим распределения сложности (по умолчанию KIDS_EASY)",
    )
    gen.add_argument("--seed", type=int, default=None, help="базовый seed для воспроизводимости")
    gen.add_argument(
        "--theme",
        default=None,
        metavar="TITLE",
        help="название темы без OpenAI (офлайн-режим; без флага тема генерируется AI)",
    )
    gen.add_argument("--child-name", default=None, help="имя ребёнка для персонализации")
    gen.add_argument("--child-age", default=None, help="возраст ребёнка (с --child-name)")
    gen.add_argument("--no-images", action="store_true", help="пропустить генерацию иллюстраций")
    gen.add_argument("--no-previews", action="store_true", help="пропустить генерацию превью")
    gen.add_argument(
        "--no-print-friendly",
        action="store_true",
        help="не генерировать ч/б print-friendly PDF даже если он включён в пресете",
    )
    return parser


def _book_config_from_args(args: argparse.Namespace) -> BookConfig:
    """Собирает BookConfig из аргументов CLI (пресет + переопределения)."""
    config = (
        personalized(args.preset, args.child_name, args.child_age)
        if args.child_name
        else PRESETS[args.preset]
    )
    if args.no_print_friendly:
        config = replace(config, generate_print_friendly_version=False)
    return config


async def _generate(args: argparse.Namespace) -> int:
    """Выполняет сценарий generate и возвращает код выхода."""
    book_config = _book_config_from_args(args)
    spec = BookSpec(
        pages_per_book=args.pages,
        maze_size=args.size,
        difficulty_mode=DifficultyMode[args.difficulty],
        book_config=book_config,
    )

    print(
        f"Генерация: {args.books} книг × {args.pages} лабиринтов, "
        f"размер {args.size[0]}x{args.size[1]}, режим {args.difficulty}, "
        f"пресет {args.preset}"
    )

    if args.child_age and not args.child_name:
        msg = "--child-age требует --child-name"
        raise ValueError(msg)

    theme = (
        build_default_theme(args.theme, book_config.language, args.pages)
        if args.theme
        else None
    )
    service = BookService()
    try:
        books = await service.generate_batch(
            spec,
            number_of_books=args.books,
            base_seed=args.seed,
            theme=theme,
            with_illustrations=not args.no_images,
            with_previews=not args.no_previews,
        )
    finally:
        container.theme_repository.close()

    if not books:
        return 1

    print(f"\nГотово! Создано {len(books)} книг:")
    for book in books:
        print(f"  - book_{book.id}: {book.theme.book_title}  ({book.output_dir})")
    return 0


def main() -> None:
    """Точка входа CLI (console script mazebook)."""
    args = build_parser().parse_args()
    if args.command == "generate":
        try:
            raise SystemExit(asyncio.run(_generate(args)))
        except ValueError as exc:
            msg = f"Ошибка генерации: {exc}"
            if "quota" in str(exc) or "credits" in str(exc):
                msg += (
                    '\nПодсказка: пополните баланс OpenAI или используйте офлайн-режим '
                    '--theme "Название книги".'
                )
            raise SystemExit(msg) from exc
        except KeyboardInterrupt:
            msg = "Прервано пользователем"
            raise SystemExit(msg) from None


if __name__ == "__main__":
    main()
