"""
routes/teacher.py — Кабинет преподавателя: дашборд + CRUD оценок.

Преподаватель видит и правит только оценки по СВОИМ предметам
(проверка на сервере, не на форме).
"""
import logging
from datetime import date, datetime

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required

from models import db, Grade, Student, Subject, Teacher
from services import analytics
from utils.decorators import teacher_required

logger = logging.getLogger(__name__)
bp = Blueprint("teacher", __name__, url_prefix="/teacher")


def _current_teacher() -> Teacher:
    teacher = current_user.teacher
    if teacher is None:
        abort(403)
    return teacher


def _own_subject_or_403(teacher: Teacher, subject_id: int) -> Subject:
    """Вернуть предмет, если он принадлежит преподавателю, иначе 403."""
    subject = db.session.get(Subject, subject_id)
    if subject is None or subject.teacher_id != teacher.id:
        abort(403)
    return subject


@bp.route("/")
@login_required
@teacher_required
def index():
    return redirect(url_for("teacher.dashboard"))


@bp.route("/dashboard")
@login_required
@teacher_required
def dashboard():
    """Дашборд преподавателя: предметы, группы, средние, группа риска."""
    teacher = _current_teacher()
    s = db.session
    subjects = analytics.teacher_subjects_overview(s, teacher.id)
    groups = analytics.teacher_groups_overview(s, teacher.id)
    student_count = sum(g["student_count"] for g in groups)
    # Средний по всем студентам препода = средневзвешенно проще взять как
    # средний по группам (для дашборда достаточно).
    avgs = [g["avg"] for g in groups if g["avg"]]
    overall = round(sum(avgs) / len(avgs), 2) if avgs else 0.0
    return render_template(
        "teacher/dashboard.html",
        subjects=subjects,
        groups=groups,
        subject_count=len(subjects),
        student_count=student_count,
        overall_avg=overall,
        at_risk=analytics.teacher_at_risk(s, teacher.id),
    )


# ---------------------------------------------------------------------------
# CRUD оценок
# ---------------------------------------------------------------------------
@bp.route("/grades")
@login_required
@teacher_required
def grades_list():
    """Список предметов препода; при ?subject_id= — студенты и их оценки."""
    teacher = _current_teacher()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).order_by(Subject.name).all()

    subject = None
    rows = []
    subject_id = request.args.get("subject_id", type=int)
    if subject_id:
        subject = _own_subject_or_403(teacher, subject_id)
        # Студенты, у которых есть оценки по этому предмету, и сами оценки.
        student_ids = (db.session.query(Grade.student_id)
                       .filter_by(subject_id=subject.id).distinct())
        students = (Student.query.filter(Student.id.in_(student_ids))
                    .all())
        for st in students:
            grades = [g for g in st.grades if g.subject_id == subject.id]
            rows.append({"student": st, "grades": grades})

    return render_template(
        "teacher/grades_list.html",
        subjects=subjects, subject=subject, rows=rows,
    )


@bp.route("/grades/add", methods=["GET", "POST"])
@login_required
@teacher_required
def grade_add():
    """Добавить оценку студенту по своему предмету."""
    teacher = _current_teacher()
    subject_id = request.values.get("subject_id", type=int)
    student_id = request.values.get("student_id", type=int)

    # Проверка владения предметом — на сервере (403 для чужого).
    subject = _own_subject_or_403(teacher, subject_id)
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)

    if request.method == "POST":
        try:
            value = float(request.form.get("value"))
            if not (2 <= value <= 5):
                raise ValueError("Балл должен быть от 2 до 5.")
            date_str = request.form.get("date") or ""
            grade_date = (datetime.strptime(date_str, "%Y-%m-%d").date()
                          if date_str else date.today())
            grade = Grade(
                student_id=student.id, subject_id=subject.id,
                value=value, date=grade_date,
                comment=(request.form.get("comment") or "").strip(),
            )
            db.session.add(grade)
            db.session.commit()
            logger.info("Препод %d добавил оценку %.1f студенту %d по предмету %d.",
                        teacher.id, value, student.id, subject.id)
            flash("Оценка добавлена.", "success")
            return redirect(url_for("teacher.grades_list", subject_id=subject.id))
        except (TypeError, ValueError) as e:
            db.session.rollback()
            flash(f"Ошибка: {e}", "danger")

    return render_template("teacher/grade_add.html", subject=subject, student=student)


@bp.route("/grades/<int:grade_id>/delete", methods=["POST"])
@login_required
@teacher_required
def grade_delete(grade_id: int):
    """Удалить оценку (только по своему предмету)."""
    teacher = _current_teacher()
    grade = db.session.get(Grade, grade_id)
    if grade is None:
        abort(404)
    # Проверка: оценка относится к предмету этого препода.
    if grade.subject.teacher_id != teacher.id:
        abort(403)
    subject_id = grade.subject_id
    db.session.delete(grade)
    db.session.commit()
    logger.info("Препод %d удалил оценку %d.", teacher.id, grade_id)
    flash("Оценка удалена.", "info")
    return redirect(url_for("teacher.grades_list", subject_id=subject_id))
