from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Конфигурация приложения MazeBookGenerator."""

    # Пути
    OUTPUT_DIR: Path = Path("output")
    TEMP_DIR: Path = Path("temp")

    # PDF настройки
    PDF_PAGE_WIDTH: float = 297.0  # A4 landscape в мм
    PDF_PAGE_HEIGHT: float = 210.0
    PDF_MARGIN: float = 20.0

    # Настройки лабиринта по умолчанию
    DEFAULT_MAZE_WIDTH: int = 20
    DEFAULT_MAZE_HEIGHT: int = 15
    DEFAULT_CELL_SIZE: float = 8.0  # мм (уменьшено для лучшего размещения)

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017/"
    MONGODB_DB_NAME: str = "maze_book_generator"
    MONGODB_COLLECTION_THEMES: str = "used_themes"

    # AI API
    OPEN_AI_KEY: str = ""
    HF_TOKEN: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

OPEN_AI_THEME_MODEL: str = "gpt-4o-mini"
OPEN_AI_THEME_TEMPERATURE: float = 0.9
OPEN_AI_THEME_SYSTEM: str = (
    "You are an assistant that generates content for children's maze books. "
    "Respond only with valid JSON in the exact format requested, no explanations."
)
OPEN_AI_THEME_PROMPT: str = (
    "Generate a UNIQUE theme for a children's maze book with {pages_count} pages.\n"
    "The following titles have already been used — DO NOT repeat or closely imitate any of them:\n"
    "{used_titles}\n"
    "Pick a completely different setting, characters, and concept.\n\n"
    "Respond strictly in JSON with no explanations, using these fields:\n"
    "  book_title — short catchy title like 'Forest Journey',\n"
    "  book_description — one sentence describing the book,\n"
    "  page_prompts — array of {pages_count} objects like:\n"
    '    {{"task": "Help the bear find honey", "heroes": ["bear", "bee"]}},\n'
    "  image_keywords — array of {pages_count} arrays of 2-4 English keywords for the illustration.\n"
    "\nExample response for 2 pages:\n"
    '{{\n'
    '  "book_title": "Forest Journey",\n'
    '  "book_description": "Help the forest animals find their way home.",\n'
    '  "page_prompts": [\n'
    '    {{"task": "Help the bear find honey", "heroes": ["bear", "bee"]}},\n'
    '    {{"task": "Guide the fox to its den", "heroes": ["fox", "rabbit"]}}\n'
    '  ],\n'
    '  "image_keywords": [["bear", "honey", "forest"], ["fox", "den"]]\n'
    "}}"
)

HF_IMAGE_MODEL: str = "black-forest-labs/FLUX.1-schnell"
HF_PROMPT_TEMPLATE: str = (
    "Children's book illustration, simple line art, {keywords}, "
    "black and white, white background, pencil sketch style, no shading"
)
IMAGE_STORAGE_SUBDIR: str = "illustrations"
WATERMARK_ALPHA: float = 0.1
