"""
routes/admin.py — Панель администратора.

ЗАГЛУШКА Этапа 1. Реальная логика — на Этапе 2.
"""
from flask import Blueprint, render_template

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
def index():
    # TODO (Этап 2): CRUD пользователей, групп, предметов; общая статистика.
    return render_template("placeholder.html", title="Панель администратора", module="admin")
