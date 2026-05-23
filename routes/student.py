"""
routes/student.py — Кабинет студента.

Дашборд наполняется на следующем шаге (аналитика). Сейчас — защита доступа.
"""
from flask import Blueprint, render_template
from flask_login import login_required

from utils.decorators import student_required

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.route("/")
@login_required
@student_required
def index():
    # TODO: дашборд студента — его оценки, средний балл, тесты.
    return render_template("placeholder.html", title="Кабинет студента", module="student")
