"""
routes/teacher.py — Кабинет преподавателя.

Дашборд наполняется на следующем шаге (аналитика). Сейчас — защита доступа.
"""
from flask import Blueprint, render_template
from flask_login import login_required

from utils.decorators import teacher_required

bp = Blueprint("teacher", __name__, url_prefix="/teacher")


@bp.route("/")
@login_required
@teacher_required
def index():
    # TODO: дашборд преподавателя — группы, оценки, аналитика.
    return render_template("placeholder.html", title="Кабинет преподавателя", module="teacher")
