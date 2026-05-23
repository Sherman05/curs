"""
services/analytics.py — Расчёты статистики успеваемости (Модуль 1).

Все функции «чистые»: принимают session первым аргументом, возвращают
примитивы / списки / словари. Запросы агрегирующие (func.avg, group_by,
join) — без N+1. Средние округляются до 2 знаков. Деление на ноль
обрабатывается (нет оценок → 0).
"""
import logging

from sqlalchemy import Integer, func

from models import Grade, Group, Student, Subject, Teacher, TestAttempt, User

logger = logging.getLogger(__name__)

RISK_THRESHOLD = 3.5  # порог группы риска по среднему баллу


def _round(value) -> float:
    """Округлить среднее до 2 знаков; None → 0."""
    return round(value, 2) if value is not None else 0.0


# ---------------------------------------------------------------------------
# Студент
# ---------------------------------------------------------------------------
def student_avg(session, student_id: int) -> float:
    """Общий средний балл студента."""
    avg = session.query(func.avg(Grade.value)).filter(
        Grade.student_id == student_id).scalar()
    return _round(avg)


def student_avg_by_subject(session, student_id: int) -> list[dict]:
    """Средний балл студента по каждому предмету: [{subject, avg, count}]."""
    rows = (session.query(
                Subject.name,
                func.avg(Grade.value),
                func.count(Grade.id))
            .join(Grade, Grade.subject_id == Subject.id)
            .filter(Grade.student_id == student_id)
            .group_by(Subject.id)
            .order_by(Subject.name)
            .all())
    return [{"subject": name, "avg": _round(avg), "count": cnt}
            for name, avg, cnt in rows]


def student_grades(session, student_id: int, limit: int | None = None) -> list[dict]:
    """Оценки студента (новые сверху): [{subject, value, date, comment}]."""
    q = (session.query(Subject.name, Grade.value, Grade.date, Grade.comment)
         .join(Subject, Subject.id == Grade.subject_id)
         .filter(Grade.student_id == student_id)
         .order_by(Grade.date.desc()))
    if limit:
        q = q.limit(limit)
    return [{"subject": s, "value": v, "date": d, "comment": c}
            for s, v, d, c in q.all()]


# ---------------------------------------------------------------------------
# Группа
# ---------------------------------------------------------------------------
def group_avg(session, group_id: int) -> float:
    """Средний балл группы (по всем оценкам её студентов)."""
    avg = (session.query(func.avg(Grade.value))
           .join(Student, Student.id == Grade.student_id)
           .filter(Student.group_id == group_id)
           .scalar())
    return _round(avg)


def group_avg_by_subject(session, group_id: int) -> list[dict]:
    """Средний балл группы по предметам: [{subject, avg}]."""
    rows = (session.query(Subject.name, func.avg(Grade.value))
            .join(Grade, Grade.subject_id == Subject.id)
            .join(Student, Student.id == Grade.student_id)
            .filter(Student.group_id == group_id)
            .group_by(Subject.id)
            .order_by(Subject.name)
            .all())
    return [{"subject": name, "avg": _round(avg)} for name, avg in rows]


# ---------------------------------------------------------------------------
# Преподаватель
# ---------------------------------------------------------------------------
def teacher_groups_overview(session, teacher_id: int) -> list[dict]:
    """Обзор по группам, где препод ведёт предмет:
    [{group_name, avg, student_count}].

    'Ведёт в группе' = у студентов группы есть оценки по предметам препода.
    """
    rows = (session.query(
                Group.name,
                func.avg(Grade.value),
                func.count(func.distinct(Student.id)))
            .join(Student, Student.group_id == Group.id)
            .join(Grade, Grade.student_id == Student.id)
            .join(Subject, Subject.id == Grade.subject_id)
            .filter(Subject.teacher_id == teacher_id)
            .group_by(Group.id)
            .order_by(Group.name)
            .all())
    return [{"group_name": name, "avg": _round(avg), "student_count": cnt}
            for name, avg, cnt in rows]


def teacher_subjects_overview(session, teacher_id: int) -> list[dict]:
    """Обзор по предметам препода: [{subject, avg, student_count}]."""
    rows = (session.query(
                Subject.name,
                func.avg(Grade.value),
                func.count(func.distinct(Grade.student_id)))
            .outerjoin(Grade, Grade.subject_id == Subject.id)
            .filter(Subject.teacher_id == teacher_id)
            .group_by(Subject.id)
            .order_by(Subject.name)
            .all())
    return [{"subject": name, "avg": _round(avg), "student_count": cnt or 0}
            for name, avg, cnt in rows]


def teacher_at_risk(session, teacher_id: int) -> list[dict]:
    """Студенты препода (учатся по его предметам) с общим средним < порога."""
    # Студенты, у которых есть оценки по предметам этого препода.
    student_ids = [r[0] for r in
                   (session.query(func.distinct(Grade.student_id))
                    .join(Subject, Subject.id == Grade.subject_id)
                    .filter(Subject.teacher_id == teacher_id).all())]
    rows = (session.query(User.full_name, Group.name, func.avg(Grade.value))
            .join(Student, Student.user_id == User.id)
            .join(Group, Group.id == Student.group_id)
            .join(Grade, Grade.student_id == Student.id)
            .filter(Student.id.in_(student_ids))
            .group_by(Student.id)
            .having(func.avg(Grade.value) < RISK_THRESHOLD)
            .order_by(func.avg(Grade.value))
            .all())
    return [{"full_name": fn, "group": gr, "avg": _round(avg)}
            for fn, gr, avg in rows]


# ---------------------------------------------------------------------------
# Топ / группа риска (общие)
# ---------------------------------------------------------------------------
def top_students(session, limit: int = 10) -> list[dict]:
    """Топ студентов по общему среднему: [{full_name, group, avg}]."""
    rows = (session.query(User.full_name, Group.name, func.avg(Grade.value))
            .join(Student, Student.user_id == User.id)
            .join(Group, Group.id == Student.group_id)
            .join(Grade, Grade.student_id == Student.id)
            .group_by(Student.id)
            .order_by(func.avg(Grade.value).desc())
            .limit(limit)
            .all())
    return [{"full_name": fn, "group": gr, "avg": _round(avg)}
            for fn, gr, avg in rows]


def at_risk_students(session) -> list[dict]:
    """Все студенты с общим средним < порога: [{full_name, group, avg}]."""
    rows = (session.query(User.full_name, Group.name, func.avg(Grade.value))
            .join(Student, Student.user_id == User.id)
            .join(Group, Group.id == Student.group_id)
            .join(Grade, Grade.student_id == Student.id)
            .group_by(Student.id)
            .having(func.avg(Grade.value) < RISK_THRESHOLD)
            .order_by(func.avg(Grade.value))
            .all())
    return [{"full_name": fn, "group": gr, "avg": _round(avg)}
            for fn, gr, avg in rows]


# ---------------------------------------------------------------------------
# Распределение оценок и общая статистика
# ---------------------------------------------------------------------------
def grade_distribution(session, scope: str = "all", scope_id=None) -> dict:
    """Распределение оценок {2: n, 3: n, 4: n, 5: n} (округление к целому).

    scope: 'all' | 'student' | 'group'.
    """
    bucket = func.cast(func.round(Grade.value), Integer)
    q = session.query(bucket, func.count(Grade.id))

    if scope == "student":
        q = q.filter(Grade.student_id == scope_id)
    elif scope == "group":
        q = (q.join(Student, Student.id == Grade.student_id)
              .filter(Student.group_id == scope_id))

    q = q.group_by(bucket)

    result = {2: 0, 3: 0, 4: 0, 5: 0}
    for grade_value, count in q.all():
        gv = int(grade_value)
        gv = min(5, max(2, gv))  # на всякий случай зажимаем в 2..5
        result[gv] += count
    return result


def overall_stats(session) -> dict:
    """Сводка для админ-дашборда."""
    overall_avg = session.query(func.avg(Grade.value)).scalar()
    return {
        "total_students": session.query(func.count(Student.id)).scalar(),
        "total_teachers": session.query(func.count(Teacher.id)).scalar(),
        "total_groups": session.query(func.count(Group.id)).scalar(),
        "total_subjects": session.query(func.count(Subject.id)).scalar(),
        "overall_avg": _round(overall_avg),
        "at_risk_count": len(at_risk_students(session)),
    }


def passed_tests_count(session, student_id: int) -> int:
    """Количество пройденных студентом тестов."""
    return (session.query(func.count(TestAttempt.id))
            .filter(TestAttempt.student_id == student_id).scalar()) or 0
