"""
services/ai_service.py — Сервис работы с LLM (Anthropic Claude).

Отвечает за:
  - генерацию учебных материалов (теория, конспект, задачи, контрольная);
  - генерацию тестов в СТРОГОМ JSON-формате (для автопроверки);
  - логирование обращений в таблицу ai_generation_logs.

ВАЖНО (надёжность к дедлайну):
  - Если ключ ANTHROPIC_API_KEY не задан или сети нет — сервис работает
    в "demo-режиме" и возвращает корректную заглушку, чтобы приложение
    не падало и его можно было показать. См. _is_configured().
  - Для тестов используется tool-use (структурированный вывод по JSON-схеме),
    чтобы ответ гарантированно парсился.
"""
import json
import logging

from flask import current_app

logger = logging.getLogger(__name__)

# JSON-схема одного теста — передаётся Claude как "инструмент",
# что заставляет модель вернуть строго структурированный ответ.
TEST_JSON_SCHEMA = {
    "name": "save_test",
    "description": "Сохранить сгенерированный тест с вопросами и вариантами ответов.",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "description": "Список вопросов теста.",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Текст вопроса"},
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Варианты ответа (2-5 штук)",
                        },
                        "correct": {
                            "type": "integer",
                            "description": "Индекс правильного варианта (с 0)",
                        },
                        "points": {
                            "type": "integer",
                            "description": "Баллы за верный ответ",
                        },
                    },
                    "required": ["question", "options", "correct", "points"],
                },
            }
        },
        "required": ["questions"],
    },
}


def _is_configured() -> bool:
    """Задан ли API-ключ. Если нет — работаем в demo-режиме."""
    return bool(current_app.config.get("AI_API_KEY"))


def _get_client():
    """Создать клиент Anthropic. Импорт внутри функции — чтобы приложение
    запускалось даже без установленного пакета (для demo-режима)."""
    from anthropic import Anthropic
    return Anthropic(api_key=current_app.config["AI_API_KEY"])


def generate_material(topic: str, material_type: str, subject_name: str,
                      teacher_id: int | None = None) -> dict:
    """Сгенерировать учебный материал (текстовый).

    Возвращает dict: {"content": str, "model": str, "tokens": int}.
    На Этапе 2 здесь будет полноценный промпт под каждый тип материала.
    """
    # TODO (Этап 2): подобрать промпт под material_type, вызвать Claude,
    #   записать в AIGenerationLog, вернуть результат.
    if not _is_configured():
        logger.warning("AI не настроен (нет ключа) — возвращаю demo-материал.")
        return {
            "content": f"[DEMO] Материал по теме «{topic}» "
                       f"({material_type}) для предмета «{subject_name}». "
                       f"Задайте ANTHROPIC_API_KEY для реальной генерации.",
            "model": "demo",
            "tokens": 0,
        }
    raise NotImplementedError("Реализация генерации — на Этапе 2 (AI-модуль).")


def generate_test(topic: str, subject_name: str, num_questions: int = 5,
                  teacher_id: int | None = None) -> dict:
    """Сгенерировать тест в строгом JSON через tool-use Claude.

    Возвращает dict: {"questions": [...], "total_points": int, "model": str}.
    """
    # TODO (Этап 2): вызвать Claude с tools=[TEST_JSON_SCHEMA],
    #   распарсить tool_use-ответ, посчитать total_points, залогировать.
    if not _is_configured():
        logger.warning("AI не настроен (нет ключа) — возвращаю demo-тест.")
        demo_questions = [{
            "question": f"[DEMO] Вопрос {i + 1} по теме «{topic}»?",
            "options": ["Вариант A", "Вариант B", "Вариант C"],
            "correct": 0,
            "points": 1,
        } for i in range(num_questions)]
        return {
            "questions": demo_questions,
            "total_points": num_questions,
            "model": "demo",
        }
    raise NotImplementedError("Реализация генерации теста — на Этапе 2.")


def check_test(questions: list[dict], answers: list[int]) -> float:
    """Автопроверка теста: сравнить ответы студента с правильными.

    questions — список вопросов (как в Test.questions_json).
    answers   — список выбранных студентом индексов вариантов.
    Возвращает суммарный набранный балл.
    """
    score = 0.0
    for i, question in enumerate(questions):
        # Студент мог не ответить на часть вопросов — защищаемся от IndexError.
        if i < len(answers) and answers[i] == question.get("correct"):
            score += question.get("points", 1)
    return score
