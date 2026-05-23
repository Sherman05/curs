"""
models/user.py — Модель пользователя и аутентификация.

User — общая таблица для всех ролей (студент / преподаватель / администратор).
Конкретные данные роли хранятся в связанных таблицах Student / Teacher
(см. models/academic.py).
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from models import db


# Допустимые роли пользователей в системе.
ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"
ROLE_ADMIN = "admin"
VALID_ROLES = (ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN)


class User(UserMixin, db.Model):
    """Учётная запись пользователя.

    UserMixin даёт Flask-Login методы is_authenticated, get_id() и т.д.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STUDENT)
    full_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Связь "один-к-одному" с профилями роли.
    # uselist=False — у пользователя максимум один профиль студента/преподавателя.
    student = db.relationship(
        "Student", back_populates="user", uselist=False,
        cascade="all, delete-orphan",
    )
    teacher = db.relationship(
        "Teacher", back_populates="user", uselist=False,
        cascade="all, delete-orphan",
    )

    # --- Работа с паролем (хешируем, никогда не храним в открытом виде) ---
    def set_password(self, password: str) -> None:
        """Захешировать и сохранить пароль."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Проверить введённый пароль против хеша."""
        return check_password_hash(self.password_hash, password)

    # --- Удобные проверки роли (используются в шаблонах и декораторах) ---
    @property
    def is_student(self) -> bool:
        return self.role == ROLE_STUDENT

    @property
    def is_teacher(self) -> bool:
        return self.role == ROLE_TEACHER

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    def __repr__(self) -> str:
        return f"<User {self.login} ({self.role})>"
