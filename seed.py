"""
seed.py — Заполнение БД тестовыми данными.

Создаёт:
  - 1 администратора,
  - 5 преподавателей,
  - 3 группы по ~10 студентов (всего 30 студентов),
  - 8 предметов,
  - ~200 оценок (часть студентов специально в "группе риска"),
  - немного записей о посещаемости.

Запуск:  flask --app app seed

ВНИМАНИЕ: если в БД уже есть пользователи — функция прервётся, чтобы не
плодить дубликаты. Чтобы пересоздать данные, удалите файл instance/coursework.db
и запустите команду заново.
"""
import logging
import random
from datetime import date, timedelta

from faker import Faker

from models import (
    db, User, Group, Student, Teacher, Subject, Grade, Attendance,
)
from models.user import ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT

logger = logging.getLogger(__name__)
fake = Faker("ru_RU")

# Фиксируем seed для воспроизводимости тестовых данных.
random.seed(42)
Faker.seed(42)

# Единый пароль для всех демо-аккаунтов (только для разработки!).
DEMO_PASSWORD = "password"

# Названия предметов для генерации.
SUBJECT_NAMES = [
    "Базы данных", "Программирование на Python", "Веб-технологии",
    "Математический анализ", "Дискретная математика", "Операционные системы",
    "Архитектура ИС", "Машинное обучение",
]

DEPARTMENTS = ["Кафедра ИСиТ", "Кафедра математики", "Кафедра информатики"]
POSITIONS = ["доцент", "профессор", "старший преподаватель", "ассистент"]
FACULTIES = ["Факультет информационных технологий"]


def _make_user(login: str, role: str, full_name: str, email: str) -> User:
    """Создать пользователя с захешированным паролем."""
    user = User(login=login, role=role, full_name=full_name, email=email)
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    return user


def seed_database() -> dict:
    """Заполнить БД тестовыми данными. Возвращает статистику созданного."""
    # Защита от повторного запуска.
    if db.session.query(User).count() > 0:
        msg = ("В БД уже есть данные. Удалите instance/coursework.db "
               "для пересоздания.")
        logger.warning(msg)
        return {"статус": msg}

    logger.info("Начинаю генерацию тестовых данных...")

    # --- 1. Администратор ---
    _make_user("admin", ROLE_ADMIN, "Администратор Системы", "admin@university.ru")

    # --- 2. Преподаватели ---
    teachers = []
    for i in range(1, 6):
        u = _make_user(f"teacher{i}", ROLE_TEACHER, fake.name(),
                       f"teacher{i}@university.ru")
        db.session.flush()  # получаем u.id
        t = Teacher(user_id=u.id,
                    department=random.choice(DEPARTMENTS),
                    position=random.choice(POSITIONS))
        db.session.add(t)
        teachers.append(t)
    db.session.flush()

    # --- 3. Группы ---
    groups = []
    for idx, name in enumerate(["ИСиТ-301", "ИСиТ-302", "ПИ-303"], start=1):
        g = Group(name=name, course=3, faculty=FACULTIES[0])
        db.session.add(g)
        groups.append(g)
    db.session.flush()

    # --- 4. Предметы (привязываем к преподавателям) ---
    subjects = []
    for i, sname in enumerate(SUBJECT_NAMES):
        s = Subject(name=sname,
                    semester=random.choice([5, 6]),
                    teacher_id=teachers[i % len(teachers)].id)
        db.session.add(s)
        subjects.append(s)
    db.session.flush()

    # --- 5. Студенты (30 штук, ~10 на группу) ---
    students = []
    for i in range(1, 31):
        u = _make_user(f"student{i}", ROLE_STUDENT, fake.name(),
                       f"student{i}@university.ru")
        db.session.flush()
        st = Student(user_id=u.id,
                     group_id=groups[(i - 1) % len(groups)].id,
                     student_card_number=f"2023{i:04d}")
        db.session.add(st)
        students.append(st)
    db.session.flush()

    # --- 6. Оценки (~200) ---
    # Часть студентов делаем "слабыми" (для группы риска, ср.балл < 3.5).
    weak_student_ids = {s.id for s in students[:6]}  # первые 6 — в группе риска
    grades_count = 0
    today = date.today()
    for st in students:
        # Каждому студенту 6-8 оценок по случайным предметам.
        for subj in random.sample(subjects, random.randint(6, 8)):
            if st.id in weak_student_ids:
                value = random.choice([2, 3, 3, 3, 4])      # слабые
            else:
                value = random.choice([3, 4, 4, 5, 5])      # обычные
            g = Grade(
                student_id=st.id,
                subject_id=subj.id,
                value=float(value),
                date=today - timedelta(days=random.randint(1, 120)),
                comment=random.choice(["", "", "Контрольная", "Лабораторная", "Экзамен"]),
            )
            db.session.add(g)
            grades_count += 1

    # --- 7. Посещаемость (по несколько записей на студента) ---
    attendance_count = 0
    for st in students:
        for subj in random.sample(subjects, 3):
            a = Attendance(
                student_id=st.id,
                subject_id=subj.id,
                date=today - timedelta(days=random.randint(1, 30)),
                present=random.random() > 0.2,  # ~80% посещений
            )
            db.session.add(a)
            attendance_count += 1

    db.session.commit()
    logger.info("Тестовые данные успешно сохранены.")

    return {
        "администраторов": 1,
        "преподавателей": len(teachers),
        "групп": len(groups),
        "предметов": len(subjects),
        "студентов": len(students),
        "оценок": grades_count,
        "записей посещаемости": attendance_count,
        "пароль для всех аккаунтов": DEMO_PASSWORD,
    }
