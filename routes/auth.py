"""
routes/auth.py — Аутентификация: вход, выход, регистрация студентов.

Регистрация публично доступна ТОЛЬКО студентам (с выбором группы).
Преподавателей и администраторов создаёт администратор (Модуль 1, Этап 2).
"""
import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import db, Group, Student, User
from models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER
from routes.forms import LoginForm, StudentRegisterForm

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__, url_prefix="/auth")


def _dashboard_for(user: User) -> str:
    """Куда перенаправить пользователя после входа — по его роли."""
    if user.role == ROLE_ADMIN:
        return url_for("admin.index")
    if user.role == ROLE_TEACHER:
        return url_for("teacher.index")
    return url_for("student.index")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Вход в систему."""
    # Уже авторизованных сразу отправляем в их кабинет.
    if current_user.is_authenticated:
        return redirect(_dashboard_for(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(login=form.login.data).first()
        # Проверяем и существование пользователя, и пароль (без раскрытия деталей).
        if user is None or not user.check_password(form.password.data):
            flash("Неверный логин или пароль.", "danger")
            logger.warning("Неудачный вход для логина '%s'.", form.login.data)
            return render_template("auth/login.html", form=form)

        login_user(user)
        logger.info("Пользователь '%s' вошёл в систему.", user.login)
        flash(f"Добро пожаловать, {user.full_name}!", "success")

        # Поддержка ?next= (куда хотел попасть пользователь до входа).
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):  # защита от open redirect
            return redirect(next_page)
        return redirect(_dashboard_for(user))

    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Саморегистрация студента."""
    if current_user.is_authenticated:
        return redirect(_dashboard_for(current_user))

    form = StudentRegisterForm()
    # Динамически подгружаем список групп в выпадающий список.
    form.group_id.choices = [
        (g.id, g.name) for g in Group.query.order_by(Group.name).all()
    ]

    if form.validate_on_submit():
        try:
            # 1. Создаём учётную запись (роль — всегда student).
            user = User(
                login=form.login.data,
                full_name=form.full_name.data,
                email=form.email.data or None,
                role=ROLE_STUDENT,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # получаем user.id до коммита

            # 2. Создаём профиль студента.
            student = Student(
                user_id=user.id,
                group_id=form.group_id.data,
                student_card_number=form.student_card_number.data,
            )
            db.session.add(student)
            db.session.commit()

            logger.info("Зарегистрирован студент '%s'.", user.login)
            flash("Регистрация успешна! Теперь войдите в систему.", "success")
            return redirect(url_for("auth.login"))
        except Exception:
            db.session.rollback()
            logger.exception("Ошибка при регистрации студента.")
            flash("Произошла ошибка при регистрации. Попробуйте ещё раз.", "danger")

    return render_template("auth/register.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    """Выход из системы."""
    logger.info("Пользователь '%s' вышел из системы.", current_user.login)
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("auth.login"))
