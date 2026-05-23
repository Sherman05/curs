"""
routes/admin.py — Панель администратора.

CRUD пользователей/групп/предметов добавляется на следующем шаге.
Сейчас — защита доступа.
"""
from flask import Blueprint, render_template
from flask_login import login_required

from utils.decorators import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@admin_required
def index():
    # TODO: CRUD пользователей, групп, предметов; общая статистика.
    return render_template("placeholder.html", title="Панель администратора", module="admin")
