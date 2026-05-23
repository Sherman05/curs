"""
services/export.py — Экспорт отчётов в PDF (reportlab) и Excel (openpyxl).

ЗАГЛУШКА Этапа 1 (сигнатуры). Полная реализация на Этапе 2.
"""
import logging

logger = logging.getLogger(__name__)


def export_grades_excel(student_ids: list[int]) -> bytes:
    """Сформировать Excel-отчёт по оценкам. Возвращает байты файла."""
    raise NotImplementedError("Этап 2: экспорт в Excel.")


def export_report_pdf(context: dict) -> bytes:
    """Сформировать PDF-отчёт. Возвращает байты файла."""
    raise NotImplementedError("Этап 2: экспорт в PDF.")
