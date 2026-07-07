from flask import Flask, jsonify, send_from_directory

from .config import Config
from .extensions import db, migrate, login_manager, csrf, cors
from .utils import ensure_runtime_dirs

from .api.routes import api_bp
from .admin.routes import admin_bp


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # ==========================================================
    # Инициализация расширений
    # ==========================================================
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Включаем CSRF
    csrf.init_app(app)

    cors.init_app(
        app,
        supports_credentials=True,
        resources={
            r"/api/*": {
                "origins": app.config["CORS_ORIGINS"]
            }
        }
    )

    # ==========================================================
    # Flask-Login
    # ==========================================================
    login_manager.login_view = None

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

    # ==========================================================
    # Создание необходимых директорий
    # ==========================================================
    ensure_runtime_dirs(app)

    # ==========================================================
    # Регистрация Blueprint
    # ==========================================================
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # ==========================================================
    # API работает через fetch(), поэтому исключаем его из CSRF
    # ==========================================================
    csrf.exempt(api_bp)
    csrf.exempt(admin_bp)

    # ==========================================================
    # Раздача загруженных файлов
    # ==========================================================
    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            filename
        )

    # ==========================================================
    # Обработчики ошибок
    # ==========================================================
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": "not_found"
        }), 404

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({
            "success": False,
            "error": "file_too_large"
        }), 413

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()

        return jsonify({
            "success": False,
            "error": "internal_server_error"
        }), 500

    # ==========================================================
    # Создание таблиц и администратора
    # ==========================================================
    with app.app_context():

        from .models import User

        db.create_all()

        admin = User.query.filter_by(username="admin").first()

        if admin is None:
            admin = User(
                username="admin",
                is_admin=True
            )

            admin.set_password("admin123")

            db.session.add(admin)
            db.session.commit()

            print("=" * 60)
            print("Создан администратор")
            print("Логин : admin")
            print("Пароль: admin123")
            print("=" * 60)

    return app