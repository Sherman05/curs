"""
routes/admin.py — Панель администратора: общий дашборд + просмотр оценок.
"""
import logging

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
from flask_login import login_required

from models import db, Grade
from services import analytics
from utils.decorators import admin_required

logger = logging.getLogger(__name__)
bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@admin_required
def index():
    return redirect(url_for("admin.dashboard"))


@bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """Общая статистика: карточки, распределение оценок, топ, группа риска."""
    s = db.session
    return render_template(
        "admin/dashboard.html",
        stats=analytics.overall_stats(s),
        distribution=analytics.grade_distribution(s, scope="all"),
        top=analytics.top_students(s, limit=10),
        at_risk=analytics.at_risk_students(s),
    )


@bp.route("/grades")
@login_required
@admin_required
def grades():
    """Все оценки с пагинацией (50 на страницу)."""
    page = request.args.get("page", 1, type=int)
    pagination = (Grade.query
                  .order_by(Grade.date.desc())
                  .paginate(page=page, per_page=50, error_out=False))
    return render_template("admin/grades.html", pagination=pagination)


@bp.route("/grades/<int:grade_id>/delete", methods=["POST"])
@login_required
@admin_required
def grade_delete(grade_id: int):
    """Удалить оценку (админ видит все)."""
    grade = db.session.get(Grade, grade_id)
    if grade is None:
        abort(404)
    page = request.args.get("page", 1, type=int)
    db.session.delete(grade)
    db.session.commit()
    logger.info("Админ удалил оценку %d.", grade_id)
    flash("Оценка удалена.", "info")
    return redirect(url_for("admin.grades", page=page))
