"""
services/import_csv.py — Импорт оценок из CSV (pandas).

ЗАГЛУШКА Этапа 1 (сигнатуры). Полная реализация на Этапе 2.
Ожидаемый формат CSV: student_card_number, subject_name, value, date, comment.
"""
import logging

logger = logging.getLogger(__name__)


def import_grades_from_csv(file_path: str) -> dict:
    """Импортировать оценки из CSV-файла.

    Возвращает dict со статистикой: {"imported": int, "errors": [...]}.
    """
    raise NotImplementedError("Этап 2: импорт CSV.")
