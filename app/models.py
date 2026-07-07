from __future__ import annotations
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager
from .utils import slugify

# === TimestampMixin ===
class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# === User (администратор) ===
class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=True, nullable=False)

    # Блокировка
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def reset_failed_attempts(self):
        self.failed_attempts = 0
        self.locked_until = None

    def increment_failed_attempts(self):
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(hours=5)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# === Категория ===
class Category(TimestampMixin, db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(120), nullable=False)
    name_en = db.Column(db.String(120), nullable=True)
    name_kg = db.Column(db.String(120), nullable=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    show_on_main = db.Column(db.Boolean, default=True, nullable=False)  # показывать на главной
    image_path = db.Column(db.String(255), default='', nullable=False)

    def __init__(self, **kwargs):
        if 'slug' not in kwargs and 'name_ru' in kwargs:
            kwargs['slug'] = slugify(kwargs['name_ru'])
        super().__init__(**kwargs)

    def get_name(self, lang='ru'):
        return getattr(self, f'name_{lang}', None) or self.name_ru

# === Товар ===
class Product(TimestampMixin, db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    title_ru = db.Column(db.String(255), nullable=False)
    title_en = db.Column(db.String(255), nullable=True)
    title_kg = db.Column(db.String(255), nullable=True)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    code = db.Column(db.String(80), unique=True, nullable=True, index=True)
    description_ru = db.Column(db.Text, default='', nullable=False)
    description_en = db.Column(db.Text, default='', nullable=True)
    description_kg = db.Column(db.Text, default='', nullable=True)
    price = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    unit = db.Column(db.String(20), default='шт', nullable=False)
    in_stock = db.Column(db.Boolean, default=True, nullable=False)
    is_popular = db.Column(db.Boolean, default=False, nullable=False)   # для главной
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    image_path = db.Column(db.String(255), default='', nullable=False)  # основное изображение
    # Дополнительные изображения (JSON или отдельная таблица)
    extra_images = db.Column(db.Text, default='', nullable=False)  # храним как JSON-массив
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category = db.relationship('Category', backref=db.backref('products', lazy=True, order_by='Product.sort_order'))

    def __init__(self, **kwargs):
        if 'slug' not in kwargs and 'title_ru' in kwargs:
            kwargs['slug'] = slugify(kwargs['title_ru'])
        super().__init__(**kwargs)

    def get_title(self, lang='ru'):
        return getattr(self, f'title_{lang}', None) or self.title_ru

    def get_description(self, lang='ru'):
        return getattr(self, f'description_{lang}', None) or self.description_ru

# === Баннер ===
class Banner(TimestampMixin, db.Model):
    __tablename__ = 'banners'

    id = db.Column(db.Integer, primary_key=True)
    title_ru = db.Column(db.String(255), default='', nullable=False)
    title_en = db.Column(db.String(255), default='', nullable=True)
    title_kg = db.Column(db.String(255), default='', nullable=True)
    subtitle_ru = db.Column(db.String(255), default='', nullable=False)
    subtitle_en = db.Column(db.String(255), default='', nullable=True)
    subtitle_kg = db.Column(db.String(255), default='', nullable=True)
    cta_ru = db.Column(db.String(120), default='Подробнее', nullable=False)
    cta_en = db.Column(db.String(120), default='Learn more', nullable=True)
    cta_kg = db.Column(db.String(120), default='Толугураак', nullable=True)
    image_path = db.Column(db.String(255), default='', nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    def get_title(self, lang='ru'):
        return getattr(self, f'title_{lang}', None) or self.title_ru

    def get_subtitle(self, lang='ru'):
        return getattr(self, f'subtitle_{lang}', None) or self.subtitle_ru

    def get_cta(self, lang='ru'):
        return getattr(self, f'cta_{lang}', None) or self.cta_ru

# === Настройки сайта ===
class SiteSettings(TimestampMixin, db.Model):
    __tablename__ = 'site_settings'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), default='ostore', nullable=False)
    logo_path = db.Column(db.String(255), default='', nullable=False)
    phone_primary = db.Column(db.String(64), default='+996 (700) 123-456', nullable=False)
    phone_secondary = db.Column(db.String(64), default='', nullable=False)
    address_ru = db.Column(db.String(255), default='г. Бишкек, ул. Советская 123', nullable=False)
    address_en = db.Column(db.String(255), default='Bishkek, Sovetskaya str. 123', nullable=True)
    address_kg = db.Column(db.String(255), default='Бишкек ш., Советская көч. 123', nullable=True)
    whatsapp = db.Column(db.String(64), default='', nullable=False)
    instagram = db.Column(db.String(64), default='', nullable=False)
    footer_about_ru = db.Column(db.Text, default='Магазин промышленных электротоваров SAMSUNG.', nullable=False)
    footer_about_en = db.Column(db.Text, default='Industrial SAMSUNG electrical equipment store.', nullable=True)
    footer_about_kg = db.Column(db.Text, default='SAMSUNG өнөр жай электр буюмдары дүкөнү.', nullable=True)
    footer_copyright = db.Column(db.String(255), default='© ostore. Все права защищены.', nullable=False)
    # 2GIS ссылка (может быть статичной)

    @classmethod
    def get_singleton(cls):
        obj = cls.query.first()
        if not obj:
            obj = cls()
            db.session.add(obj)
            db.session.commit()
        return obj

    def get_address(self, lang='ru'):
        return getattr(self, f'address_{lang}', None) or self.address_ru

    def get_footer_about(self, lang='ru'):
        return getattr(self, f'footer_about_{lang}', None) or self.footer_about_ru