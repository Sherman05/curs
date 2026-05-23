"""
app.py — Точка входа приложения (фабрика Flask-приложения).

Здесь:
  - создаётся и настраивается Flask-приложение (create_app);
  - инициализируются расширения: SQLAlchemy, Flask-Login, Migrate, CSRF;
  - регистрируются blueprint'ы (маршруты);
  - настраивается логирование;
  - объявляются CLI-команды: `flask init-db` и `flask seed`.

Запуск (для разработки):
    flask --app app run --debug
или просто:
    python app.py
"""
import logging
import os

from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect

from config import config_by_name
from models import db, User

# --- Расширения (создаём здесь, инициализируем в create_app) ---
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def configure_logging(app: Flask) -> None:
    """Настроить логирование в консоль с понятным форматом."""
    logging.basicConfig(
        level=logging.INFO if not app.debug else logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.logger.info("Логирование настроено.")


@login_manager.user_loader
def load_user(user_id: str):
    """Flask-Login: как загрузить пользователя по id из сессии."""
    return db.session.get(User, int(user_id))


def create_app(config_name: str | None = None) -> Flask:
    """Фабрика приложения. Позволяет создавать разные конфигурации
    (development / production / testing) и упрощает тестирование."""
    app = Flask(__name__, instance_relative_config=True)

    # Выбираем конфигурацию (по умолчанию development).
    config_name = config_name or os.getenv("FLASK_CONFIG", "default")
    app.config.from_object(config_by_name[config_name])

    # Гарантируем существование папки instance/ (для SQLite-файла).
    os.makedirs(app.instance_path, exist_ok=True)

    # --- Инициализация расширений ---
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)            # CSRF-защита всех форм
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Пожалуйста, войдите в систему."
    login_manager.login_message_category = "warning"

    configure_logging(app)

    # Создаём отсутствующие таблицы при старте (SQLite подхватит новые модели
    # без миграций; существующие таблицы не трогаются).
    with app.app_context():
        db.create_all()

    # --- Регистрация blueprint'ов (маршрутов) ---
    from routes import auth, student, teacher, admin, ai_routes
    app.register_blueprint(auth.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(teacher.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(ai_routes.bp)

    # --- Главная страница ---
    @app.route("/")
    def index():
        return render_template("index.html")

    # --- Обработчики ошибок (понятные сообщения) ---
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("placeholder.html",
                               title="Доступ запрещён (403)",
                               module="error"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("placeholder.html",
                               title="Страница не найдена (404)",
                               module="error"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Внутренняя ошибка сервера")
        return render_template("placeholder.html",
                               title="Внутренняя ошибка (500)",
                               module="error"), 500

    # --- CLI-команды ---
    register_cli(app)

    return app


def register_cli(app: Flask) -> None:
    """Зарегистрировать команды управления БД."""

    @app.cli.command("init-db")
    def init_db():
        """Создать все таблицы БД (без тестовых данных)."""
        db.create_all()
        app.logger.info("Таблицы БД созданы.")
        print("OK: таблицы созданы.")

    @app.cli.command("seed")
    def seed():
        """Создать таблицы и заполнить БД тестовыми данными."""
        from seed import seed_database
        db.create_all()
        stats = seed_database()
        print("OK: тестовые данные загружены.")
        for key, val in stats.items():
            print(f"  {key}: {val}")


# Объект приложения для `flask --app app` и для `python app.py`.
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
