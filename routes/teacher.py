"""
routes/teacher.py — Кабинет преподавателя.

ЗАГЛУШКА Этапа 1. Реальная логика — на Этапе 2.
"""
from flask import Blueprint, render_template

bp = Blueprint("teacher", __name__, url_prefix="/teacher")


@bp.route("/")
def index():
    # TODO (Этап 2): дашборд преподавателя — группы, оценки, аналитика.
    return render_template("placeholder.html", title="Кабинет преподавателя", module="teacher")
