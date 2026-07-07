from flask import jsonify

from flask_cors import CORS
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# ==========================================================
# База данных
# ==========================================================
db = SQLAlchemy()

# ==========================================================
# Миграции
# ==========================================================
migrate = Migrate()

# ==========================================================
# Авторизация
# ==========================================================
login_manager = LoginManager()

# Для API отключаем редиректы на страницу входа
login_manager.login_view = None

# Защита сессии
login_manager.session_protection = "strong"

# Сообщения Flask-Login отключаем, так как это REST API
login_manager.login_message = None
login_manager.login_message_category = None

# ==========================================================
# CSRF
# ==========================================================
csrf = CSRFProtect()

# ==========================================================
# CORS
# ==========================================================
cors = CORS()

# ==========================================================
# Обработка неавторизованного доступа
# ==========================================================
@login_manager.unauthorized_handler
def unauthorized():
    return (
        jsonify(
            {
                "success": False,
                "error": "Unauthorized",
                "message": "Authentication required"
            }
        ),
        401,
    )