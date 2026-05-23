"""
routes/student.py — Кабинет студента.

ЗАГЛУШКА Этапа 1. Реальная логика — на Этапе 2.
"""
from flask import Blueprint, render_template

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.route("/")
def index():
    # TODO (Этап 2): дашборд студента — его оценки, средний балл, тесты.
    return render_template("placeholder.html", title="Кабинет студента", module="student")
