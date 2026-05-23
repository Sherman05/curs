"""
models/__init__.py — Инициализация ORM и сбор всех моделей в одном месте.

Здесь создаётся единственный экземпляр SQLAlchemy (db), который затем
подключается к Flask-приложению в app.py через db.init_app(app).

Импортируем все модели сюда, чтобы при `from models import db, User, ...`
они были доступны, а Alembic/SQLAlchemy "видели" все таблицы.
"""
from flask_sqlalchemy import SQLAlchemy

# Единый объект доступа к БД для всего приложения.
db = SQLAlchemy()

# Импорт моделей ПОСЛЕ создания db, чтобы избежать циклических импортов.
from models.user import User  # noqa: E402
from models.academic import (  # noqa: E402
    Group,
    Student,
    Teacher,
    Subject,
    Grade,
    Attendance,
)
from models.ai_module import (  # noqa: E402
    Material,
    Test,
    TestAttempt,
    AIGenerationLog,
)

# Список экспортируемых имён (удобно для `from models import *`).
__all__ = [
    "db",
    "User",
    "Group",
    "Student",
    "Teacher",
    "Subject",
    "Grade",
    "Attendance",
    "Material",
    "Test",
    "TestAttempt",
    "AIGenerationLog",
]
