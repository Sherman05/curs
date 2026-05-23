"""
services/ai_service.py — Сервис работы с LLM (Anthropic Claude).

Отвечает за:
  - генерацию тестов по СТРОГОЙ JSON-схеме (для стабильной автопроверки);
  - автопроверку прохождений;
  - логирование обращений в таблицу ai_generation_logs.

JSON-схема ответа модели (генерация теста):
{
  "title": "string",
  "questions": [
    {"text": "string", "options": ["A","B","C","D"], "correct_index": 0, "points": 1}
  ]
}

НАДЁЖНОСТЬ:
  - Если ANTHROPIC_API_KEY не задан — сервис работает в demo-режиме и
    возвращает корректный по схеме тест, чтобы приложение можно было
    показать без ключа.
  - При сбое парсинга реального ответа делается ОДНА повторная попытка,
    затем — понятная ошибка (RuntimeError), а не traceback пользователю.
"""
import json
import logging
import re

from flask import current_app

from models import db, AIGenerationLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _is_configured() -> bool:
    """Задан ли API-ключ. Если нет — работаем в demo-режиме."""
    return bool(current_app.config.get("AI_API_KEY"))


def _get_client():
    """Создать клиент Anthropic (импорт внутри — чтобы demo-режим работал
    даже без сетевых вызовов)."""
    from anthropic import Anthropic
    return Anthropic(api_key=current_app.config["AI_API_KEY"])


def _build_prompt(subject_name: str, topic: str, question_count: int) -> str:
    """Промпт с явным требованием вернуть ТОЛЬКО JSON по схеме."""
    return (
        f"Ты — преподаватель предмета «{subject_name}». "
        f"Составь тест из {question_count} вопросов с вариантами ответов "
        f"по теме «{topic}».\n\n"
        "Требования:\n"
        f"- ровно {question_count} вопросов;\n"
        "- у каждого вопроса 4 варианта ответа;\n"
        "- только один правильный вариант;\n"
        "- вопросы на русском языке, по сути темы.\n\n"
        "Верни ОТВЕТ СТРОГО в формате JSON без пояснений и markdown:\n"
        '{\n'
        '  "title": "Название теста",\n'
        '  "questions": [\n'
        '    {"text": "Текст вопроса", "options": ["A","B","C","D"], '
        '"correct_index": 0, "points": 1}\n'
        '  ]\n'
        '}\n'
    )


def _extract_json(raw: str) -> dict:
    """Достать JSON из ответа модели (срезаем markdown-обёртку, лишний текст)."""
    text = raw.strip()
    # Убираем ```json ... ``` если есть.
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # Берём содержимое от первой { до последней }.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("В ответе модели не найден JSON.")
    return json.loads(text[start:end + 1])


def _validate_test(data: dict, expected_count: int) -> dict:
    """Проверить структуру теста. Возвращает нормализованный dict.

    Бросает ValueError при некорректной структуре.
    """
    if not isinstance(data, dict):
        raise ValueError("Ответ не является объектом JSON.")
    title = str(data.get("title") or "").strip() or "Тест"
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("Отсутствует непустой список вопросов.")

    normalized = []
    for i, q in enumerate(questions):
        text = str(q.get("text") or "").strip()
        options = q.get("options")
        if not text:
            raise ValueError(f"Вопрос {i + 1}: пустой текст.")
        if not isinstance(options, list) or len(options) < 2:
            raise ValueError(f"Вопрос {i + 1}: нужно минимум 2 варианта ответа.")
        options = [str(o) for o in options]
        correct = q.get("correct_index")
        if not isinstance(correct, int) or not (0 <= correct < len(options)):
            raise ValueError(
                f"Вопрос {i + 1}: correct_index вне диапазона вариантов.")
        points = q.get("points", 1)
        if not isinstance(points, int) or points <= 0:
            points = 1
        normalized.append({
            "text": text, "options": options,
            "correct_index": correct, "points": points,
        })

    if len(normalized) != expected_count:
        # Не критично (модель могла дать чуть больше/меньше) — только лог.
        logger.warning("Запрошено %d вопросов, получено %d.",
                       expected_count, len(normalized))

    return {"title": title, "questions": normalized}


def _log_generation(teacher_id, prompt: str, response: str, tokens: int) -> None:
    """Записать обращение к LLM в журнал (для аудита и подсчёта токенов)."""
    try:
        log = AIGenerationLog(
            teacher_id=teacher_id, prompt=prompt,
            response=response, tokens_used=tokens,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Не удалось записать лог генерации AI.")


def _demo_test(subject_name: str, topic: str, question_count: int) -> dict:
    """Корректный по схеме тест для работы без API-ключа."""
    questions = [{
        "text": f"[DEMO] Вопрос {i + 1} по теме «{topic}» "
                f"(предмет «{subject_name}»)?",
        "options": ["Вариант A", "Вариант B", "Вариант C", "Вариант D"],
        "correct_index": i % 4,
        "points": 1,
    } for i in range(question_count)]
    return {"title": f"Тест по теме «{topic}»", "questions": questions}


def _call_model(client, prompt: str) -> tuple[str, int]:
    """Вызвать Claude, вернуть (текст ответа, количество токенов)."""
    msg = client.messages.create(
        model=current_app.config["AI_MODEL"],   # claude-sonnet-4-5
        max_tokens=2000,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    tokens = msg.usage.input_tokens + msg.usage.output_tokens
    return text, tokens


# ---------------------------------------------------------------------------
# Публичный API сервиса
# ---------------------------------------------------------------------------
def generate_test(subject_name: str, topic: str, question_count: int = 10,
                  teacher_id: int | None = None) -> dict:
    """Сгенерировать тест по строгой JSON-схеме.

    Возвращает dict: {"title": str, "questions": [...]}.
    Бросает RuntimeError с понятным сообщением при неустранимой ошибке AI.
    """
    prompt = _build_prompt(subject_name, topic, question_count)

    # --- Demo-режим (нет ключа) ---
    if not _is_configured():
        logger.warning("AI не настроен (нет ключа) — генерирую demo-тест.")
        data = _demo_test(subject_name, topic, question_count)
        _log_generation(teacher_id, prompt, json.dumps(data, ensure_ascii=False), 0)
        return _validate_test(data, question_count)

    # --- Боевой режим (вызов Claude) ---
    try:
        client = _get_client()
    except Exception as e:
        logger.exception("Не удалось создать клиент Anthropic.")
        raise RuntimeError("AI-сервис недоступен: проверьте установку пакета "
                           "anthropic и ключ ANTHROPIC_API_KEY.") from e

    raw, tokens = "", 0
    try:
        raw, tokens = _call_model(client, prompt)
        data = _validate_test(_extract_json(raw), question_count)
    except Exception as first_err:
        # Одна повторная попытка с усиленным требованием формата.
        logger.warning("Первый ответ AI не распарсился (%s). Повтор...", first_err)
        try:
            retry_prompt = prompt + "\n\nВАЖНО: верни ТОЛЬКО валидный JSON, без текста."
            raw2, tokens2 = _call_model(client, retry_prompt)
            tokens += tokens2
            raw = raw + "\n---retry---\n" + raw2
            data = _validate_test(_extract_json(raw2), question_count)
        except Exception as e:
            _log_generation(teacher_id, prompt, f"ОШИБКА: {raw}", tokens)
            logger.exception("AI не смог сгенерировать корректный тест.")
            raise RuntimeError(
                "Не удалось сгенерировать тест: модель вернула некорректный "
                "формат. Попробуйте изменить тему или повторить попытку."
            ) from e

    _log_generation(teacher_id, prompt, raw, tokens)
    logger.info("Тест сгенерирован: %d вопросов, токенов=%d.",
                len(data["questions"]), tokens)
    return data


def generate_remedial_tasks(subject_name: str, weak_topics: list[str]) -> dict:
    """Сгенерировать дополнительные задачи по слабым темам (адаптивка).

    TODO (Этап 5): реализовать генерацию доп. задач для группы риска.
    """
    raise NotImplementedError("Адаптивное обучение — Этап 5.")


def score_attempt(test_data: dict, answers: dict) -> tuple[float, list[dict]]:
    """Автопроверка прохождения теста.

    test_data — {"title":..., "questions":[...]} (как в Test.questions_json).
    answers   — {индекс_вопроса(str|int): выбранный_вариант(int)}.

    Возвращает (набранный_балл, разбор), где разбор — список по вопросам:
    [{"text", "options", "correct_index", "chosen", "is_correct", "points"}].
    """
    score = 0.0
    details = []
    for i, q in enumerate(test_data["questions"]):
        chosen = answers.get(str(i), answers.get(i))  # ключ может быть str или int
        chosen = int(chosen) if chosen is not None and str(chosen) != "" else None
        is_correct = chosen == q["correct_index"]
        if is_correct:
            score += q["points"]
        details.append({
            "text": q["text"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "chosen": chosen,
            "is_correct": is_correct,
            "points": q["points"],
        })
    return score, details
