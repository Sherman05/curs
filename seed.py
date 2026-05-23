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

    db.session.flush()

    # --- 8. Демо-объекты для защиты (готовый тест, попытка, доп. задачи) ---
    # Эти объекты не зависят от AI — чтобы на защите всё работало без ключа.
    demo = _seed_demo_objects(subjects, students)

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
        "демо-тест": demo["test"],
        "демо-прохождение": demo["attempt"],
        "демо-доп.задачи": demo["remedial"],
        "пароль для всех аккаунтов": DEMO_PASSWORD,
    }


def _seed_demo_objects(subjects: list, students: list) -> dict:
    """Создать готовые демо-объекты (тест, попытку, доп. задачи) без AI."""
    import json

    from models import Material, Test, TestAttempt, RemedialAssignment
    from models.ai_module import MATERIAL_TEST
    from services import ai_service

    # Предмет для демо-теста — «Базы данных».
    subj_db = next((s for s in subjects if s.name == "Базы данных"), subjects[0])

    # Готовый тест с фиксированными вопросами (не зависит от AI).
    test_data = {
        "title": "Демонстрационный тест: основы баз данных",
        "questions": [
            {"text": "Что такое первичный ключ (PRIMARY KEY)?",
             "options": ["Уникальный идентификатор строки",
                         "Любой индекс таблицы",
                         "Внешняя ссылка на другую таблицу",
                         "Команда удаления"],
             "correct_index": 0, "points": 1},
            {"text": "Какая команда выбирает данные из таблицы?",
             "options": ["INSERT", "SELECT", "UPDATE", "DELETE"],
             "correct_index": 1, "points": 1},
            {"text": "Что обеспечивает нормализация БД?",
             "options": ["Ускорение сети",
                         "Снижение избыточности данных",
                         "Шифрование паролей",
                         "Резервное копирование"],
             "correct_index": 1, "points": 1},
            {"text": "Что делает оператор JOIN?",
             "options": ["Удаляет таблицу",
                         "Объединяет строки из нескольких таблиц",
                         "Создаёт пользователя",
                         "Сортирует индекс"],
             "correct_index": 1, "points": 1},
        ],
    }
    material = Material(
        teacher_id=subj_db.teacher_id, subject_id=subj_db.id,
        topic="Основы баз данных", type=MATERIAL_TEST,
        content=test_data["title"], ai_model_used="demo",
    )
    db.session.add(material)
    db.session.flush()
    test = Test(
        material_id=material.id,
        questions_json=json.dumps(test_data, ensure_ascii=False),
        total_points=sum(q["points"] for q in test_data["questions"]),
    )
    db.session.add(test)
    db.session.flush()

    # Демо-прохождение: НЕ слабый студент (students[:6] — слабые), изучающий
    # «Базы данных». Так student1 остаётся без попытки и может пройти тест
    # вживую на защите, а у преподавателя уже есть результат для показа.
    attempt_student = next(
        (st for st in students[6:]
         if any(g.subject_id == subj_db.id for g in st.grades)), None)
    attempt_created = False
    if attempt_student:
        answers = {"0": 0, "1": 1, "2": 1, "3": 0}  # последний — неверный
        score, _ = ai_service.score_attempt(test_data, answers)
        db.session.add(TestAttempt(
            student_id=attempt_student.id, test_id=test.id,
            answers_json=json.dumps(answers, ensure_ascii=False), score=score,
        ))
        attempt_created = True

    # Демо-доп.задачи для слабого студента (первый из «слабых» — students[0]).
    weak_student = students[0]
    weak_grade = weak_student.grades[0] if weak_student.grades else None
    remedial_created = False
    if weak_grade:
        remedial_data = {
            "subject": next(s.name for s in subjects if s.id == weak_grade.subject_id),
            "tasks": [
                {"topic": "Базовые понятия", "text": "Повторите ключевые определения "
                 "темы и решите 3 задачи из методички.",
                 "hint": "Начните с примеров, разобранных на лекции.",
                 "approach": "Пошаговый разбор условия и применение формул."},
                {"topic": "Практика", "text": "Решите типовую задачу средней сложности.",
                 "hint": "Используйте алгоритм из конспекта.",
                 "approach": "Декомпозиция задачи на подзадачи."},
            ],
        }
        db.session.add(RemedialAssignment(
            student_id=weak_student.id, subject_id=weak_grade.subject_id,
            content_json=json.dumps(remedial_data, ensure_ascii=False),
        ))
        remedial_created = True

    # Демо-конспект лекции и демо-теория (предмет «Базы данных»).
    from models.ai_module import MATERIAL_LECTURE, MATERIAL_THEORY
    lecture_data = {
        "title": "Конспект лекции: реляционная модель данных",
        "introduction": "Реляционная модель описывает данные в виде таблиц "
                        "(отношений), связанных по ключам.",
        "sections": [
            {"heading": "Таблицы и отношения",
             "content": "Данные хранятся в таблицах. Строка — запись, столбец — атрибут.",
             "key_points": ["Таблица = отношение", "Строка = кортеж"]},
            {"heading": "Ключи",
             "content": "Первичный ключ однозначно идентифицирует строку; внешний "
                        "ключ ссылается на первичный ключ другой таблицы.",
             "key_points": ["PRIMARY KEY уникален", "FOREIGN KEY обеспечивает целостность"]},
            {"heading": "Нормализация",
             "content": "Нормализация снижает избыточность и устраняет аномалии "
                        "обновления за счёт декомпозиции таблиц.",
             "key_points": ["1НФ, 2НФ, 3НФ", "Меньше дублирования данных"]},
        ],
        "summary": "Реляционная модель — основа большинства современных СУБД.",
    }
    db.session.add(Material(
        teacher_id=subj_db.teacher_id, subject_id=subj_db.id,
        topic="Реляционная модель данных", type=MATERIAL_LECTURE,
        content=json.dumps(lecture_data, ensure_ascii=False), ai_model_used="demo"))

    theory_data = {
        "title": "Теория: язык SQL",
        "definitions": [
            {"term": "SQL", "definition": "язык структурированных запросов к реляционным БД."},
            {"term": "DDL", "definition": "подмножество SQL для определения структуры (CREATE, ALTER)."},
            {"term": "DML", "definition": "подмножество SQL для работы с данными (SELECT, INSERT)."},
        ],
        "concepts": [
            {"name": "Выборка данных", "explanation": "Оператор SELECT извлекает строки "
             "по условию.", "example": "SELECT * FROM students WHERE group_id = 1;"},
            {"name": "Соединение таблиц", "explanation": "JOIN объединяет строки из "
             "нескольких таблиц по условию.", "example": "SELECT ... FROM grades JOIN subjects ON ..."},
        ],
        "summary": "SQL — стандартный язык работы с реляционными базами данных.",
    }
    db.session.add(Material(
        teacher_id=subj_db.teacher_id, subject_id=subj_db.id,
        topic="Язык SQL", type=MATERIAL_THEORY,
        content=json.dumps(theory_data, ensure_ascii=False), ai_model_used="demo"))

    return {
        "test": material.topic,
        "attempt": "создано" if attempt_created else "нет",
        "remedial": "создано" if remedial_created else "нет",
        "лекция+теория": "создано",
    }
