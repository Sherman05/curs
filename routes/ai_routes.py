"""
routes/ai_routes.py — Маршруты AI-модуля (генерация материалов, тесты).

ЗАГЛУШКА Этапа 1. Реальная логика — на Этапе 2.
"""
from flask import Blueprint, render_template

bp = Blueprint("ai", __name__, url_prefix="/ai")


@bp.route("/")
def index():
    # TODO (Этап 2): мастер генерации материалов (предмет→тема→тип).
    return render_template("placeholder.html", title="AI-генератор материалов", module="ai")
