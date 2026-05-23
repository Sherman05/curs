"""
routes/forms.py — Формы (Flask-WTF) с валидацией и CSRF-защитой.

Flask-WTF автоматически добавляет CSRF-токен в каждую форму (см. {{ form.hidden_tag() }}
в шаблонах), что защищает от межсайтовой подделки запросов.
"""
from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, Optional, ValidationError,
)

from models import Student, User


class LoginForm(FlaskForm):
    """Форма входа в систему."""
    login = StringField("Логин", validators=[DataRequired(), Length(3, 64)])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")


class StudentRegisterForm(FlaskForm):
    """Форма саморегистрации студента (с выбором группы).

    Преподавателей и администраторов создаёт только администратор —
    публичной регистрации для них нет.
    """
    login = StringField("Логин", validators=[DataRequired(), Length(3, 64)])
    full_name = StringField("ФИО", validators=[DataRequired(), Length(3, 128)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=128)])
    student_card_number = StringField(
        "Номер студенческого билета", validators=[DataRequired(), Length(3, 20)],
    )
    # Список групп подгружается в маршруте (choices задаются динамически).
    group_id = SelectField("Группа", coerce=int, validators=[DataRequired()])
    password = PasswordField(
        "Пароль", validators=[DataRequired(), Length(min=6, message="Минимум 6 символов")],
    )
    password2 = PasswordField(
        "Повтор пароля",
        validators=[DataRequired(), EqualTo("password", message="Пароли не совпадают")],
    )
    submit = SubmitField("Зарегистрироваться")

    # --- Кастомная валидация уникальности (вызывается WTForms автоматически) ---
    def validate_login(self, field):
        if User.query.filter_by(login=field.data).first():
            raise ValidationError("Этот логин уже занят.")

    def validate_email(self, field):
        if field.data and User.query.filter_by(email=field.data).first():
            raise ValidationError("Этот email уже зарегистрирован.")

    def validate_student_card_number(self, field):
        if Student.query.filter_by(student_card_number=field.data).first():
            raise ValidationError("Студент с таким номером билета уже существует.")
