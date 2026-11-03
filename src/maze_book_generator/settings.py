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
    "Pick a completely different setting, characters, and concept.\n"
    "This book is sold on marketplaces, so generate practical SEO-friendly marketplace copy, not generic ad poetry.\n"
    "Use these product facts exactly as constraints:\n"
    "- Language: {language_name}\n"
    "- Book title hint: {book_title_hint}\n"
    "- Theme hint: {theme_hint}\n"
    "- Age range: {age_range}\n"
    "- Maze count: {pages_count}\n"
    "- Answers included: {answers_included}\n"
    "- Printable version included: {print_friendly}\n"
    "- Format: PDF\n"
    "- Product type: DIGITAL download\n"
    "- Physical shipping: NOT provided\n\n"
    "Marketplace audience: parents, teachers, home learning, travel activities, screen-free quiet time.\n"
    "Benefits to mention in marketplace_description: attention, logic, persistence, fine motor skills, calm screen-free activity.\n"
    "Do not claim physical delivery, shipping, or printed book.\n"
    "Do not promise features not present in facts.\n"
    "For regular book data, keep fields concise and thematic.\n"
    "Generate additional dedicated marketplace fields.\n"
    "marketplace_title must be concise and include key phrases: 'maze book for kids', 'printable PDF', age range (e.g. 'ages 4-7'), maze count when natural, and 'answers included' if it fits.\n"
    "marketplace_description must be structured with short sections (about 450-700 characters total), using this exact order:\n"
    "1) Short intro sentence\n"
    "2) Benefits sentence\n"
    "3) What's included sentence/list\n"
    "4) Use cases sentence\n"
    "5) Digital disclaimer sentence saying this is a digital product and no physical book is shipped.\n\n"
    "Task quality rules for page_prompts.task:\n"
    "- Use clear everyday goals a child can instantly understand.\n"
    "- The destination must be logically connected to the hero (bear→honey, squirrel→acorn, pirate→treasure chest).\n"
    "- Avoid abstract, weird, or unnatural targets (no 'owl to reading furniture', no metaphorical objects).\n"
    "- Keep each task short, natural, and action-based (5-12 words).\n"
    "- Vary heroes and targets across pages; avoid near-duplicate tasks.\n\n"
    "Respond strictly in JSON with no explanations, using these fields:\n"
    "  book_title — short catchy title for the book theme,\n"
    "  book_description — short thematic description (1-2 sentences),\n"
    "  marketplace_title — selling title in English for marketplaces,\n"
    "  marketplace_description — structured selling description in English, about 450-700 characters,\n"
    "  page_prompts — array of {pages_count} objects like:\n"
    '    {{"task": "Help the bear find honey", "heroes": ["bear", "bee"]}},\n'
    "  image_keywords — array of {pages_count} arrays of 2-4 English keywords for the illustration.\n"
    "\nExample response for 2 pages:\n"
    '{{\n'
    '  "book_title": "Forest Journey",\n'
    '  "book_description": "Help forest animals find their way home through fun maze adventures.",\n'
    '  "marketplace_title": "Maze Book for Kids Ages 4-7, Printable PDF with Answers",\n'
    '  "marketplace_description": "Digital maze book for kids ages 4-7 in printable PDF format. Activities support attention, logic, persistence, and fine motor development through playful practice. Includes 2 mazes, answer pages, and a child-friendly instruction page; printable version is included. Great for home learning, travel, classroom breaks, and calm screen-free time. This is a digital product: no physical book is shipped.",\n'
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
    "Выбери совершенно другое окружение, персонажей и концепцию.\n"
    "Книга планируется для продажи на маркетплейсах, поэтому нужен практичный SEO-friendly текст, а не абстрактная реклама.\n"
    "Используй эти факты о товаре как обязательные ограничения:\n"
    "- Язык книги: {language_name}\n"
    "- Подсказка названия: {book_title_hint}\n"
    "- Подсказка темы: {theme_hint}\n"
    "- Возраст: {age_range}\n"
    "- Количество лабиринтов: {pages_count}\n"
    "- Ответы: {answers_included}\n"
    "- Версия для печати: {print_friendly}\n"
    "- Формат: PDF\n"
    "- Тип товара: цифровой\n"
    "- Физическая отправка: отсутствует\n\n"
    "Целевая аудитория маркетплейса: родители, педагоги, занятия дома и в дороге, спокойный досуг без гаджетов.\n"
    "Пользу в marketplace_description обязательно обозначь: внимание, логика, усидчивость, мелкая моторика, спокойные занятия без гаджетов.\n"
    "Не обещай то, чего нет в фактах. Не пиши про доставку и физическую книгу.\n"
    "Обычные поля книги оставь краткими и тематическими.\n"
    "Дополнительно сгенерируй отдельные поля для маркетплейса.\n"
    "marketplace_title должен быть коротким и включать ключи: 'лабиринты для детей', 'PDF', 'для печати', возраст (например '4-7 лет'), по возможности количество заданий и пометку про ответы.\n"
    "marketplace_description должен быть структурированным (примерно 450-700 символов) и идти в таком порядке:\n"
    "1) Короткое вступление\n"
    "2) Польза\n"
    "3) Что входит\n"
    "4) Где использовать\n"
    "5) Важное предупреждение, что это цифровой товар и физическая книга не отправляется.\n\n"
    "Требования к качеству page_prompts.task:\n"
    "- Формулируй задания простым и понятным для ребенка языком.\n"
    "- Цель должна быть естественно связана с героем (медведь→мёд, белка→орех, пират→сундук).\n"
    "- Избегай странных, абстрактных и нелепых формулировок (например, 'сову к мебели для чтения').\n"
    "- Держи каждое задание коротким, конкретным и глагольным (примерно 5-12 слов).\n"
    "- Разнообразь задания по страницам, не делай почти одинаковые формулировки.\n\n"
    "Ответь строго в JSON без пояснений, используя эти поля:\n"
    "  book_title — короткое тематическое название книги на русском,\n"
    "  book_description — краткое тематическое описание книги на русском (1-2 предложения),\n"
    "  marketplace_title — продающее название книги на русском для маркетплейса,\n"
    "  marketplace_description — структурированное продающее описание на русском, примерно 450-700 символов,\n"
    "  page_prompts — массив из {pages_count} объектов вида:\n"
    '    {{"task": "Помоги медведю найти мёд", "heroes": ["медведь", "пчела"]}},\n'
    "  image_keywords — массив из {pages_count} массивов по 2-4 ключевых слова "
    "на английском для иллюстраций.\n"
    "\nПример ответа для 2 страниц:\n"
    '{{\n'
    '  "book_title": "Лесное путешествие",\n'
    '  "book_description": "Помоги лесным зверятам найти дорогу домой через веселые лабиринты.",\n'
    '  "marketplace_title": "Лабиринты для детей 4-7 лет PDF для печати, 2 задания с ответами",\n'
    '  "marketplace_description": "Цифровая книга с лабиринтами для детей 4-7 лет в формате PDF. Задания помогают развивать внимание, логику, усидчивость и мелкую моторику в спокойном темпе. Внутри 2 лабиринта, ответы ко всем заданиям и версия для печати. Подходит для занятий дома, в дороге и для досуга без гаджетов вместе с родителями или педагогом. Это цифровой товар: физическая книга не отправляется, после покупки вы получаете PDF-файл.",\n'
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
    "{keywords}, simple line art, black and white, plain pure white background, "
    "centered full composition, no crop, no frame, no border, no vignette, no dark backdrop, "
    "clean bold outlines, happy playful mood, kawaii, coloring book style, no shading"
)
IMAGE_STORAGE_SUBDIR: str = "illustrations"
WATERMARK_ALPHA: float = 0.1
WATERMARK_BG_DIFF_THRESHOLD: int = 18
WATERMARK_BG_DIFF_GAIN: float = 2.8
WATERMARK_EDGE_FADE_INSET_RATIO: float = 0.14
WATERMARK_EDGE_FADE_BLUR_RATIO: float = 0.07

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
