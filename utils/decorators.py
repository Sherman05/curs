"""
utils/decorators.py — Декораторы контроля доступа по ролям.

Используются над маршрутами, чтобы пускать только пользователей нужной роли:

    @bp.route("/")
    @teacher_required
    def index(): ...

Если роль не подходит — отдаём 403 (доступ запрещён).
"""
from functools import wraps

from flask import abort
from flask_login import current_user

from models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER


def role_required(*roles):
    """Базовый декоратор: пускает только пользователей с одной из ролей.

    Требует, чтобы пользователь был авторизован (иначе Flask-Login сам
    перенаправит на страницу входа через @login_required-логику)."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


# Готовые декораторы под конкретные роли (для удобства и читаемости).
def student_required(view):
    return role_required(ROLE_STUDENT)(view)


def teacher_required(view):
    return role_required(ROLE_TEACHER)(view)


def admin_required(view):
    return role_required(ROLE_ADMIN)(view)
