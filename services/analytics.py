"""
services/analytics.py — Расчёты статистики успеваемости (Модуль 1).

ЗАГЛУШКА Этапа 1 (сигнатуры). Полная реализация на Этапе 2.
Здесь будут: средний балл, распределение оценок, топ студентов,
группа риска (средний балл < RISK_THRESHOLD).
"""
import logging

logger = logging.getLogger(__name__)


def average_grade(student_id: int) -> float:
    """Средний балл студента по всем предметам."""
    raise NotImplementedError("Этап 2: аналитика.")


def grade_distribution(group_id: int | None = None) -> dict:
    """Распределение оценок (для Chart.js): {оценка: количество}."""
    raise NotImplementedError("Этап 2: аналитика.")


def top_students(limit: int = 10) -> list:
    """Топ студентов по среднему баллу."""
    raise NotImplementedError("Этап 2: аналитика.")


def risk_group(threshold: float = 3.5) -> list:
    """Студенты из 'группы риска' (средний балл < threshold)."""
    raise NotImplementedError("Этап 2: аналитика.")
