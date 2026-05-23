"""
routes/student.py — Кабинет студента: прохождение тестов с автопроверкой.

Маршруты (все под @student_required):
  GET  /student/                      — кабинет (заглушка, дашборд позже)
  GET  /student/tests                 — доступные тесты по своим предметам
  GET  /student/tests/<id>            — форма прохождения
  POST /student/tests/<id>/submit     — автопроверка и запись попытки
  GET  /student/tests/<id>/result     — результат с разбором

Доступ к тесту: только если тест относится к предмету, который изучает
студент (есть хотя бы одна оценка по этому предмету). Повторное
прохождение запрещено — редирект на результат.
"""
import json
import logging

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required

from models import db, Grade, Material, Student, Test, TestAttempt
from models.ai_module import MATERIAL_TEST
from services import ai_service, analytics
from utils.decorators import student_required

logger = logging.getLogger(__name__)
bp = Blueprint("student", __name__, url_prefix="/student")


def _current_student() -> Student:
    """Профиль студента текущего пользователя."""
    student = current_user.student
    if student is None:
        abort(403)
    return student


def _student_subject_ids(student: Student) -> set[int]:
    """ID предметов, которые изучает студент (есть оценки) — его 'свои' предметы."""
    rows = db.session.query(Grade.subject_id).filter_by(student_id=student.id).distinct()
    return {r[0] for r in rows}


def _attempt_for(student: Student, test: Test) -> TestAttempt | None:
    """Найти попытку прохождения теста этим студентом (если есть)."""
    return TestAttempt.query.filter_by(student_id=student.id, test_id=test.id).first()


@bp.route("/")
@login_required
@student_required
def index():
    return redirect(url_for("student.dashboard"))


@bp.route("/dashboard")
@login_required
@student_required
def dashboard():
    """Дашборд студента: средний балл, распределение, оценки по предметам."""
    student = _current_student()
    s = db.session
    by_subject = analytics.student_avg_by_subject(s, student.id)
    dist = analytics.grade_distribution(s, scope="student", scope_id=student.id)
    return render_template(
        "student/dashboard.html",
        avg=analytics.student_avg(s, student.id),
        subject_count=len(by_subject),
        tests_passed=analytics.passed_tests_count(s, student.id),
        by_subject=by_subject,
        distribution=dist,
        last_grades=analytics.student_grades(s, student.id, limit=10),
    )


@bp.route("/tests")
@login_required
@student_required
def tests_list():
    """Доступные тесты по предметам, которые изучает студент."""
    student = _current_student()
    subject_ids = _student_subject_ids(student)

    # Материалы-тесты по этим предметам, у которых есть привязанный Test.
    materials = (Material.query
                 .filter(Material.type == MATERIAL_TEST,
                         Material.subject_id.in_(subject_ids or [-1]))
                 .order_by(Material.created_at.desc())
                 .all())

    items = []
    for m in materials:
        if not m.test:
            continue
        items.append({
            "material": m,
            "test": m.test,
            "attempt": _attempt_for(student, m.test),
        })
    return render_template("student/tests_list.html", items=items)


@bp.route("/tests/<int:test_id>")
@login_required
@student_required
def test_take(test_id: int):
    """Форма прохождения теста."""
    student = _current_student()
    test = db.session.get(Test, test_id)
    if test is None:
        abort(404)
    # Проверка доступа: тест должен относиться к изучаемому предмету.
    if test.material.subject_id not in _student_subject_ids(student):
        abort(403)
    # Повторное прохождение запрещено.
    if _attempt_for(student, test):
        flash("Вы уже проходили этот тест.", "info")
        return redirect(url_for("student.test_result", test_id=test.id))

    test_data = json.loads(test.questions_json)
    return render_template("student/test_take.html", test=test, test_data=test_data)


@bp.route("/tests/<int:test_id>/submit", methods=["POST"])
@login_required
@student_required
def test_submit(test_id: int):
    """Автопроверка ответов и запись попытки."""
    student = _current_student()
    test = db.session.get(Test, test_id)
    if test is None:
        abort(404)
    if test.material.subject_id not in _student_subject_ids(student):
        abort(403)
    if _attempt_for(student, test):
        return redirect(url_for("student.test_result", test_id=test.id))

    test_data = json.loads(test.questions_json)
    # Собираем ответы: поле q{i} = выбранный индекс.
    answers = {}
    for i in range(len(test_data["questions"])):
        val = request.form.get(f"q{i}")
        if val is not None and val != "":
            answers[str(i)] = int(val)

    score, _ = ai_service.score_attempt(test_data, answers)

    try:
        attempt = TestAttempt(
            student_id=student.id, test_id=test.id,
            answers_json=json.dumps(answers, ensure_ascii=False),
            score=score,
        )
        db.session.add(attempt)
        db.session.commit()
        logger.info("Студент %d прошёл тест %d: %.1f/%d баллов.",
                    student.id, test.id, score, test.total_points)
    except Exception:
        db.session.rollback()
        logger.exception("Ошибка при сохранении попытки прохождения теста.")
        flash("Не удалось сохранить результат. Попробуйте ещё раз.", "danger")
        return redirect(url_for("student.test_take", test_id=test.id))

    return redirect(url_for("student.test_result", test_id=test.id))


@bp.route("/tests/<int:test_id>/result")
@login_required
@student_required
def test_result(test_id: int):
    """Результат прохождения с разбором правильных/неправильных ответов."""
    student = _current_student()
    test = db.session.get(Test, test_id)
    if test is None:
        abort(404)
    attempt = _attempt_for(student, test)
    if attempt is None:
        return redirect(url_for("student.test_take", test_id=test.id))

    test_data = json.loads(test.questions_json)
    answers = json.loads(attempt.answers_json)
    score, details = ai_service.score_attempt(test_data, answers)
    return render_template(
        "student/test_result.html",
        test=test, test_data=test_data, attempt=attempt,
        score=score, details=details,
    )
