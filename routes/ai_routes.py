"""
routes/ai_routes.py — Маршруты AI-модуля (генерация материалов, тесты).

Доступ — преподавателям. Полная логика добавляется на шаге AI-модуля.
"""
from flask import Blueprint, render_template
from flask_login import login_required

from utils.decorators import teacher_required

bp = Blueprint("ai", __name__, url_prefix="/ai")


@bp.route("/")
@login_required
@teacher_required
def index():
    # TODO: мастер генерации материалов (предмет→тема→тип).
    return render_template("placeholder.html", title="AI-генератор материалов", module="ai")
