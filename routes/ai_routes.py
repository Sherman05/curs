"""
routes/ai_routes.py — AI-модуль: генерация и сохранение тестов (преподаватель).

Маршруты (все под @teacher_required):
  GET  /teacher/materials/          — список материалов преподавателя
  GET  /teacher/materials/new       — форма генерации
  POST /teacher/materials/generate  — вызов AI, редактируемая форма
  POST /teacher/materials/save      — сохранение в materials + tests
  GET  /teacher/materials/<id>      — просмотр теста + прохождения студентов
"""
import json
import logging

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required

from models import db, Material, Subject, Test, Teacher
from models.ai_module import MATERIAL_TEST, MATERIAL_LECTURE, MATERIAL_THEORY
from services import ai_service
from utils.decorators import teacher_required

logger = logging.getLogger(__name__)
bp = Blueprint("ai", __name__, url_prefix="/teacher/materials")

# Типы материалов, доступные для генерации (значение, подпись).
MATERIAL_TYPE_CHOICES = [
    (MATERIAL_TEST, "Тест с автопроверкой"),
    (MATERIAL_LECTURE, "Конспект лекции"),
    (MATERIAL_THEORY, "Теория"),
]


def _current_teacher() -> Teacher:
    """Профиль преподавателя текущего пользователя."""
    teacher = current_user.teacher
    if teacher is None:
        abort(403)
    return teacher


@bp.route("/")
@login_required
@teacher_required
def index():
    """Список материалов (тестов) преподавателя."""
    teacher = _current_teacher()
    materials = (Material.query
                 .filter_by(teacher_id=teacher.id)
                 .order_by(Material.created_at.desc())
                 .all())
    return render_template("teacher/materials_list.html", materials=materials)


@bp.route("/new")
@login_required
@teacher_required
def new():
    """Форма генерации теста: выбор предмета (только свои), тема, кол-во вопросов."""
    teacher = _current_teacher()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).order_by(Subject.name).all()
    return render_template("teacher/material_new.html", subjects=subjects,
                           material_types=MATERIAL_TYPE_CHOICES)


@bp.route("/generate", methods=["POST"])
@login_required
@teacher_required
def generate():
    """Вызов AI и рендер редактируемой формы со сгенерированными вопросами."""
    teacher = _current_teacher()
    subject_id = request.form.get("subject_id", type=int)
    topic = (request.form.get("topic") or "").strip()
    material_type = request.form.get("material_type", MATERIAL_TEST)

    subject = db.session.get(Subject, subject_id)
    # Предмет должен существовать и принадлежать этому преподавателю.
    if subject is None or subject.teacher_id != teacher.id:
        flash("Выберите свой предмет.", "danger")
        return redirect(url_for("ai.new"))
    if not topic:
        flash("Укажите тему материала.", "danger")
        return redirect(url_for("ai.new"))

    try:
        if material_type == MATERIAL_TEST:
            question_count = request.form.get("question_count", default=10, type=int)
            question_count = max(1, min(question_count, 20))
            test_data = ai_service.generate_test(
                subject_name=subject.name, topic=topic,
                question_count=question_count, teacher_id=teacher.id)
            return render_template("teacher/material_edit.html",
                                   subject=subject, topic=topic, test_data=test_data)
        elif material_type == MATERIAL_LECTURE:
            data = ai_service.generate_lecture(subject.name, topic, teacher.id)
            return render_template("teacher/material_edit_lecture.html",
                                   subject=subject, topic=topic, data=data)
        elif material_type == MATERIAL_THEORY:
            data = ai_service.generate_theory(subject.name, topic, teacher.id)
            return render_template("teacher/material_edit_theory.html",
                                   subject=subject, topic=topic, data=data)
        else:
            flash("Неизвестный тип материала.", "danger")
            return redirect(url_for("ai.new"))
    except RuntimeError as e:
        # Понятное сообщение пользователю, без traceback.
        flash(str(e), "danger")
        return redirect(url_for("ai.new"))


@bp.route("/save", methods=["POST"])
@login_required
@teacher_required
def save():
    """Сохранить отредактированный материал. Для test создаётся запись в tests,
    для lecture/theory JSON хранится в materials.content."""
    teacher = _current_teacher()
    subject_id = request.form.get("subject_id", type=int)
    topic = (request.form.get("topic") or "").strip()
    material_type = request.form.get("material_type", MATERIAL_TEST)
    title = (request.form.get("title") or topic or "Материал").strip()

    subject = db.session.get(Subject, subject_id)
    if subject is None or subject.teacher_id != teacher.id:
        abort(403)

    # Лекция и теория сохраняются как JSON в materials.content (без tests).
    if material_type in (MATERIAL_LECTURE, MATERIAL_THEORY):
        return _save_content_material(teacher, subject, topic, title, material_type)

    # Собираем вопросы из формы (поля q{i}_text, q{i}_optN, q{i}_correct, q{i}_points).
    questions = []
    i = 0
    while f"q{i}_text" in request.form:
        text = (request.form.get(f"q{i}_text") or "").strip()
        options = []
        j = 0
        while f"q{i}_opt{j}" in request.form:
            opt = (request.form.get(f"q{i}_opt{j}") or "").strip()
            if opt:
                options.append(opt)
            j += 1
        correct = request.form.get(f"q{i}_correct", default=0, type=int)
        points = request.form.get(f"q{i}_points", default=1, type=int)
        if text and len(options) >= 2 and 0 <= correct < len(options):
            questions.append({
                "text": text, "options": options,
                "correct_index": correct, "points": max(1, points),
            })
        i += 1

    if not questions:
        flash("Тест пуст или содержит ошибки — сохранять нечего.", "danger")
        return redirect(url_for("ai.new"))

    test_data = {"title": title, "questions": questions}
    total_points = sum(q["points"] for q in questions)

    try:
        material = Material(
            teacher_id=teacher.id, subject_id=subject.id,
            topic=topic, type=MATERIAL_TEST,
            content=title, ai_model_used=current_app_model(),
        )
        db.session.add(material)
        db.session.flush()  # material.id

        test = Test(
            material_id=material.id,
            questions_json=json.dumps(test_data, ensure_ascii=False),
            total_points=total_points,
        )
        db.session.add(test)
        db.session.commit()
        logger.info("Сохранён тест material=%d (%d вопросов).",
                    material.id, len(questions))
        flash("Тест сохранён.", "success")
        return redirect(url_for("ai.view", material_id=material.id))
    except Exception:
        db.session.rollback()
        logger.exception("Ошибка при сохранении теста.")
        flash("Не удалось сохранить тест. Попробуйте ещё раз.", "danger")
        return redirect(url_for("ai.new"))


def _save_content_material(teacher, subject, topic, title, material_type):
    """Собрать из формы JSON лекции/теории и сохранить в materials.content."""
    if material_type == MATERIAL_LECTURE:
        sections = []
        i = 0
        while f"sec{i}_heading" in request.form:
            heading = (request.form.get(f"sec{i}_heading") or "").strip()
            content = (request.form.get(f"sec{i}_content") or "").strip()
            kp = [ln.strip() for ln in (request.form.get(f"sec{i}_kp") or "").splitlines()
                  if ln.strip()]
            if heading and content:
                sections.append({"heading": heading, "content": content, "key_points": kp})
            i += 1
        if not sections:
            flash("Материал пуст — сохранять нечего.", "danger")
            return redirect(url_for("ai.new"))
        data = {
            "title": title,
            "introduction": (request.form.get("introduction") or "").strip(),
            "sections": sections,
            "summary": (request.form.get("summary") or "").strip(),
        }
    else:  # MATERIAL_THEORY
        definitions, concepts = [], []
        i = 0
        while f"def{i}_term" in request.form:
            term = (request.form.get(f"def{i}_term") or "").strip()
            definition = (request.form.get(f"def{i}_definition") or "").strip()
            if term and definition:
                definitions.append({"term": term, "definition": definition})
            i += 1
        i = 0
        while f"con{i}_name" in request.form:
            name = (request.form.get(f"con{i}_name") or "").strip()
            explanation = (request.form.get(f"con{i}_explanation") or "").strip()
            example = (request.form.get(f"con{i}_example") or "").strip()
            if name and explanation:
                concepts.append({"name": name, "explanation": explanation, "example": example})
            i += 1
        if not definitions and not concepts:
            flash("Материал пуст — сохранять нечего.", "danger")
            return redirect(url_for("ai.new"))
        data = {
            "title": title, "definitions": definitions, "concepts": concepts,
            "summary": (request.form.get("summary") or "").strip(),
        }

    try:
        material = Material(
            teacher_id=teacher.id, subject_id=subject.id,
            topic=topic, type=material_type,
            content=json.dumps(data, ensure_ascii=False),
            ai_model_used=current_app_model(),
        )
        db.session.add(material)
        db.session.commit()
        logger.info("Сохранён материал material=%d (тип=%s).", material.id, material_type)
        flash("Материал сохранён.", "success")
        return redirect(url_for("ai.view", material_id=material.id))
    except Exception:
        db.session.rollback()
        logger.exception("Ошибка при сохранении материала.")
        flash("Не удалось сохранить материал. Попробуйте ещё раз.", "danger")
        return redirect(url_for("ai.new"))


@bp.route("/<int:material_id>")
@login_required
@teacher_required
def view(material_id: int):
    """Просмотр материала: тест с прохождениями либо лекция/теория."""
    teacher = _current_teacher()
    material = db.session.get(Material, material_id)
    if material is None or material.teacher_id != teacher.id:
        abort(404)

    if material.type == MATERIAL_TEST:
        test = material.test
        test_data = json.loads(test.questions_json) if test else {"questions": []}
        attempts = test.attempts if test else []
        return render_template("teacher/material_view.html", material=material,
                               test=test, test_data=test_data, attempts=attempts)
    # Лекция / теория: контент хранится JSON-ом в material.content.
    content = json.loads(material.content)
    return render_template("teacher/material_view.html", material=material,
                           test=None, content=content, attempts=[])


def current_app_model() -> str:
    """Имя используемой модели (для записи в materials.ai_model_used)."""
    from flask import current_app
    return current_app.config.get("AI_MODEL", "unknown")
