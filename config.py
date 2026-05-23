"""
config.py — Конфигурация приложения.

Все секреты читаются из переменных окружения (файл .env).
Никогда не коммить реальные ключи в репозиторий!
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные окружения из .env (если файл есть)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Базовая конфигурация (используется по умолчанию)."""

    # --- Безопасность ---
    # SECRET_KEY нужен Flask для подписи сессий и CSRF-токенов.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-me")

    # --- База данных ---
    # SQLite-файл лежит в папке instance/ (создаётся автоматически).
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI",
        f"sqlite:///{BASE_DIR / 'instance' / 'coursework.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # отключаем лишние накладные расходы

    # --- AI-модуль (Anthropic Claude) ---
    AI_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    # Основная модель для генерации учебных материалов (качество).
    AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-5")
    # Дешёвая/быстрая модель для простых задач (можно переключать).
    AI_MODEL_FAST = os.getenv("AI_MODEL_FAST", "claude-haiku-4-5")
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4096"))

    # --- Загрузка файлов (импорт CSV) ---
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 МБ лимит на загружаемый файл

    # --- Бизнес-логика ---
    # Порог среднего балла, ниже которого студент попадает в "группу риска"
    # и для него включается адаптивное обучение (Модуль 3).
    RISK_THRESHOLD = float(os.getenv("RISK_THRESHOLD", "3.5"))


class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True


class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False


class TestingConfig(Config):
    """Конфигурация для тестов (БД в памяти)."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


# Словарь для выбора конфигурации по имени (через переменную FLASK_CONFIG).
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
