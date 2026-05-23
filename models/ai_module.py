"""
models/ai_module.py — Сущности AI-модуля (Модуль 2 и 3).

Содержит таблицы: materials, tests, test_attempts, ai_generation_logs.
Учебные материалы генерируются LLM (Claude), правятся преподавателем
и сохраняются здесь. Тесты проходятся студентами с автопроверкой.
"""
from datetime import datetime

from models import db


# Допустимые типы учебных материалов (Модуль 2).
MATERIAL_CONTROL = "control"       # контрольная работа
MATERIAL_TEST = "test"             # тест с автопроверкой
MATERIAL_PRACTICE = "practice"     # задачи для практики
MATERIAL_LECTURE = "lecture"       # конспект лекции
MATERIAL_THEORY = "theory"         # теория
MATERIAL_TYPES = (
    MATERIAL_CONTROL,
    MATERIAL_TEST,
    MATERIAL_PRACTICE,
    MATERIAL_LECTURE,
    MATERIAL_THEORY,
)

# Человекочитаемые названия типов (для отображения в шаблонах).
MATERIAL_TYPE_LABELS = {
    MATERIAL_CONTROL: "Контрольная работа",
    MATERIAL_TEST: "Тест с автопроверкой",
    MATERIAL_PRACTICE: "Задачи для практики",
    MATERIAL_LECTURE: "Конспект лекции",
    MATERIAL_THEORY: "Теория",
}


class Material(db.Model):
    """Учебный материал, сгенерированный AI и сохранённый преподавателем."""
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    topic = db.Column(db.String(255), nullable=False)        # тема материала
    type = db.Column(db.String(20), nullable=False)          # см. MATERIAL_TYPES
    content = db.Column(db.Text, nullable=False)             # текст материала
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ai_model_used = db.Column(db.String(64), nullable=True)  # какая модель сгенерировала

    # Адаптивное обучение (Модуль 3): материал может быть привязан к студенту,
    # которому система сгенерировала доп. задачи. NULL — материал общий для группы.
    target_student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=True,
    )

    # Связи.
    teacher = db.relationship("Teacher", back_populates="materials")
    subject = db.relationship("Subject", back_populates="materials")
    target_student = db.relationship("Student", foreign_keys=[target_student_id])
    # Если материал — тест, к нему привязан объект Test (один-к-одному).
    test = db.relationship(
        "Test", back_populates="material", uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def type_label(self) -> str:
        """Человекочитаемое название типа материала."""
        return MATERIAL_TYPE_LABELS.get(self.type, self.type)

    def __repr__(self) -> str:
        return f"<Material '{self.topic}' ({self.type})>"


class Test(db.Model):
    """Тест с автопроверкой.

    questions_json — структура вопросов в JSON (генерируется AI по схеме).
    Формат: [{"question": "...", "options": ["a","b"...],
              "correct": 0, "points": 1}, ...]
    """
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(
        db.Integer, db.ForeignKey("materials.id"), unique=True, nullable=False,
    )
    questions_json = db.Column(db.Text, nullable=False)
    total_points = db.Column(db.Integer, nullable=False, default=0)

    # Связи.
    material = db.relationship("Material", back_populates="test")
    attempts = db.relationship(
        "TestAttempt", back_populates="test", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Test #{self.id} (материал {self.material_id})>"


class TestAttempt(db.Model):
    """Попытка прохождения теста студентом (с результатом автопроверки)."""
    __tablename__ = "test_attempts"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    answers_json = db.Column(db.Text, nullable=False)        # ответы студента в JSON
    score = db.Column(db.Float, nullable=False, default=0)   # набранные баллы
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Связи.
    student = db.relationship("Student", back_populates="test_attempts")
    test = db.relationship("Test", back_populates="attempts")

    def __repr__(self) -> str:
        return f"<TestAttempt студ.{self.student_id} тест.{self.test_id} = {self.score}>"


class AIGenerationLog(db.Model):
    """Журнал обращений к LLM (для аудита, отладки и подсчёта токенов)."""
    __tablename__ = "ai_generation_logs"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)
    prompt = db.Column(db.Text, nullable=False)              # отправленный запрос
    response = db.Column(db.Text, nullable=True)             # полученный ответ
    tokens_used = db.Column(db.Integer, nullable=True)       # израсходовано токенов
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Связь.
    teacher = db.relationship("Teacher")

    def __repr__(self) -> str:
        return f"<AIGenerationLog #{self.id} токенов={self.tokens_used}>"


class RemedialAssignment(db.Model):
    """Персональные доп. задачи (адаптивное обучение, Модуль 3).

    Генерируются AI для студента, у которого средний балл по предмету < 3.5.
    content_json — сериализованный результат генерации (см. ai_service).
    """
    __tablename__ = "remedial_assignments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    content_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("Student", backref="remedial_assignments")
    subject = db.relationship("Subject")

    def __repr__(self) -> str:
        return f"<RemedialAssignment студ.{self.student_id} предм.{self.subject_id}>"
