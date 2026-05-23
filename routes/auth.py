"""
routes/auth.py — Аутентификация (вход, выход, регистрация).

ЗАГЛУШКА Этапа 1. Реальная логика — на Этапе 2.
"""
from flask import Blueprint, render_template

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login")
def login():
    # TODO (Этап 2): форма входа, проверка пароля, login_user().
    return render_template("placeholder.html", title="Вход", module="auth")
