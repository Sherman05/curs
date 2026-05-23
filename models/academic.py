"""
models/academic.py — Учебные сущности (Модуль 1: Аналитика успеваемости).

Содержит таблицы: groups, students, teachers, subjects, grades, attendance.
Все связи описаны через relationship + ForeignKey для целостности данных.
"""
from datetime import date, datetime

from models import db


class Group(db.Model):
    """Учебная группа (например, ИСиТ-301)."""
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    course = db.Column(db.Integer, nullable=False)          # курс (1-5)
    faculty = db.Column(db.String(128), nullable=False)     # факультет

    # Студенты этой группы.
    students = db.relationship(
        "Student", back_populates="group", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Group {self.name}>"


class Student(db.Model):
    """Профиль студента (расширение User для роли 'student')."""
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False,
    )
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    student_card_number = db.Column(db.String(20), unique=True, nullable=False)

    # Связи.
    user = db.relationship("User", back_populates="student")
    group = db.relationship("Group", back_populates="students")
    grades = db.relationship(
        "Grade", back_populates="student", cascade="all, delete-orphan",
    )
    attendances = db.relationship(
        "Attendance", back_populates="student", cascade="all, delete-orphan",
    )
    test_attempts = db.relationship(
        "TestAttempt", back_populates="student", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        name = self.user.full_name if self.user else "?"
        return f"<Student {name} [{self.student_card_number}]>"


class Teacher(db.Model):
    """Профиль преподавателя (расширение User для роли 'teacher')."""
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False,
    )
    department = db.Column(db.String(128), nullable=False)  # кафедра
    position = db.Column(db.String(64), nullable=False)     # должность

    # Связи.
    user = db.relationship("User", back_populates="teacher")
    subjects = db.relationship("Subject", back_populates="teacher")
    materials = db.relationship(
        "Material", back_populates="teacher", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        name = self.user.full_name if self.user else "?"
        return f"<Teacher {name}>"


class Subject(db.Model):
    """Учебный предмет/дисциплина."""
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)

    # Связи.
    teacher = db.relationship("Teacher", back_populates="subjects")
    grades = db.relationship(
        "Grade", back_populates="subject", cascade="all, delete-orphan",
    )
    materials = db.relationship(
        "Material", back_populates="subject", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Subject {self.name} (сем. {self.semester})>"


class Grade(db.Model):
    """Оценка студента по предмету.

    value — оценка по 5-балльной шкале (можно дробную, например 4.5).
    """
    __tablename__ = "grades"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    comment = db.Column(db.String(255), nullable=True)

    # Связи.
    student = db.relationship("Student", back_populates="grades")
    subject = db.relationship("Subject", back_populates="grades")

    def __repr__(self) -> str:
        return f"<Grade {self.value} (студ.{self.student_id}/предм.{self.subject_id})>"


class Attendance(db.Model):
    """Посещаемость занятия студентом."""
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    present = db.Column(db.Boolean, default=True, nullable=False)

    # Связи.
    student = db.relationship("Student", back_populates="attendances")
    subject = db.relationship("Subject")

    def __repr__(self) -> str:
        status = "был" if self.present else "пропуск"
        return f"<Attendance студ.{self.student_id} {self.date} {status}>"
