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
    REPLICATE_API_TOKEN: str = ""

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

OPEN_AI_THEME_SYSTEM_RU: str = (
    "Ты помощник, который генерирует контент для детских книг с лабиринтами. "
    "Отвечай только валидным JSON в точном запрошенном формате, без пояснений."
)
OPEN_AI_THEME_PROMPT_RU: str = (
    "Придумай УНИКАЛЬНУЮ тему для детской книги с лабиринтами на {pages_count} страниц.\n"
    "Следующие названия уже использованы — НЕ повторяй и не имитируй их:\n"
    "{used_titles}\n"
    "Выбери совершенно другое окружение, персонажей и концепцию.\n\n"
    "Ответь строго в JSON без пояснений, используя эти поля:\n"
    "  book_title — короткое броское название на русском, например 'Лесное путешествие',\n"
    "  book_description — одно предложение с описанием книги на русском,\n"
    "  page_prompts — массив из {pages_count} объектов вида:\n"
    '    {{"task": "Помоги медведю найти мёд", "heroes": ["медведь", "пчела"]}},\n'
    "  image_keywords — массив из {pages_count} массивов по 2-4 ключевых слова "
    "на английском для иллюстраций.\n"
    "\nПример ответа для 2 страниц:\n"
    '{{\n'
    '  "book_title": "Лесное путешествие",\n'
    '  "book_description": "Помоги лесным зверятам найти дорогу домой.",\n'
    '  "page_prompts": [\n'
    '    {{"task": "Помоги медведю найти мёд", "heroes": ["медведь", "пчела"]}},\n'
    '    {{"task": "Проведи лису к норке", "heroes": ["лиса", "кролик"]}}\n'
    '  ],\n'
    '  "image_keywords": [["bear", "honey", "forest"], ["fox", "den"]]\n'
    "}}"
)

HF_IMAGE_MODEL: str = "black-forest-labs/FLUX.1-schnell"

# Список моделей в порядке приоритета — при ошибке 402/429 клиент переходит к следующей
HF_IMAGE_MODEL_FALLBACKS: list[str] = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "stabilityai/stable-diffusion-2-1",        # SDv2, хорошее качество
    "runwayml/stable-diffusion-v1-5",
    "prompthero/openjourney-v4",                # Midjourney-стиль, бесплатная
    "dreamlike-art/dreamlike-photoreal-2.0",   # Мягкий иллюстративный стиль
    "Lykon/dreamshaper-8",                     # Популярная для иллюстраций
    "CompVis/stable-diffusion-v1-4",
]

IMAGE_GENERATOR_PROMPT_TEMPLATE: str = (
    "Cute cheerful children's book illustration, friendly cartoon style, "
    "{keywords}, simple line art, black and white, white background, "
    "clean bold outlines, happy playful mood, kawaii, coloring book style, no shading"
)
IMAGE_STORAGE_SUBDIR: str = "illustrations"
WATERMARK_ALPHA: float = 0.1

# Replicate — список дешёвых моделей для B&W детских иллюстраций.
# Порядок = приоритет. Клиент резолвит версию каждой и пытается сгенерировать,
# при неудаче переходит к следующей.
REPLICATE_IMAGE_MODELS: list[str] = [
    "bytedance/sdxl-lightning-4step",   # ~$0.0007/img, 4 steps
    "black-forest-labs/flux-schnell",   # ~$0.004/img, high quality
    "stability-ai/sdxl",                 # ~$0.0025/img, официальный SDXL
    "prompthero/openjourney-v4",        # ~$0.002/img, midjourney-style
    "cjwbw/anything-v3.0",               # ~$0.002/img, anime/cartoon style
]
REPLICATE_IMAGE_PARAMS: dict = {
    "width": 512,
    "height": 512,
    "num_inference_steps": 4,
    "scheduler": "K_EULER",
    "guidance_scale": 0,
}
# Задержка между запросами к Replicate для соблюдения rate limit ~6/min
REPLICATE_RATE_LIMIT_DELAY: float = 10.0

# Pollinations AI — бесплатный API для генерации изображений
# Rate limit ~6 запросов/минуту, задержка между запросами в секундах
POLLINATIONS_PARAMS: dict = {
    "width": 512,
    "height": 512,
    "nologo": "true",
}
POLLINATIONS_RATE_LIMIT_DELAY: float = 1.0
