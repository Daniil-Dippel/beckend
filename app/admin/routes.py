from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from ..extensions import db
from ..models import (
    Banner,
    Category,
    Product,
    SiteSettings,
    User,
)
from ..services import (
    banner_to_dict,
    category_to_dict,
    product_to_dict,
    settings_to_dict,
)
from ..utils import (
    build_upload_url,
    save_image,
    slugify,
)

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin",
)


def success(data=None, status=200):
    response = {
        "success": True
    }

    if data is not None:
        response["data"] = data

    return jsonify(response), status


def error(message, status=400):
    return jsonify({
        "success": False,
        "error": message
    }), status


def require_admin():
    if not current_user.is_authenticated:
        return error("Unauthorized", 401)

    if not current_user.is_admin:
        return error("Forbidden", 403)

    return None


@admin_bp.post("/login")
def login():

    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return error("Введите логин и пароль")

    user = User.query.filter_by(username=username).first()

    if not user:
        return error("Неверный логин или пароль", 401)

    if user.is_locked():

        minutes = int(
            (user.locked_until - datetime.utcnow()).total_seconds() // 60
        )

        return error(
            f"Аккаунт временно заблокирован ({minutes} мин.)",
            403
        )

    if not user.check_password(password):

        user.increment_failed_attempts()
        db.session.commit()

        if user.failed_attempts >= 5:
            return error(
                "Слишком много попыток входа. Аккаунт заблокирован.",
                403
            )

        return error("Неверный логин или пароль", 401)

    user.reset_failed_attempts()

    db.session.commit()

    login_user(
        user,
        remember=True
    )

    return success({
        "username": user.username,
        "isAdmin": user.is_admin
    })


@admin_bp.post("/logout")
@login_required
def logout():

    logout_user()

    return success()


@admin_bp.get("/me")
@login_required
def me():

    admin = require_admin()

    if admin:
        return admin

    return success({
        "username": current_user.username,
        "isAdmin": current_user.is_admin,
    })


@admin_bp.get("/categories")
@login_required
def get_categories():

    admin = require_admin()
    if admin:
        return admin

    lang = request.args.get("lang", "ru")

    categories = (
        Category.query
        .order_by(Category.sort_order.asc(), Category.id.asc())
        .all()
    )

    return success([
        category_to_dict(category, lang)
        for category in categories
    ])


@admin_bp.post("/categories")
@login_required
def create_category():

    admin = require_admin()
    if admin:
        return admin

    data = request.get_json(silent=True) or {}

    name_ru = data.get("name_ru", "").strip()

    if not name_ru:
        return error("Введите название категории")

    slug = slugify(name_ru)

    if Category.query.filter_by(slug=slug).first():
        return error("Категория уже существует")

    category = Category(
        name_ru=name_ru,
        name_en=data.get("name_en", "").strip(),
        name_kg=data.get("name_kg", "").strip(),
        slug=slug,
        sort_order=int(data.get("sort_order", 0)),
        show_on_main=bool(data.get("show_on_main", True)),
    )

    db.session.add(category)
    db.session.commit()

    return success(
        category_to_dict(category),
        201
    )


@admin_bp.put("/categories/<int:category_id>")
@login_required
def update_category(category_id):

    admin = require_admin()
    if admin:
        return admin

    category = db.session.get(Category, category_id)

    if category is None:
        return error("Категория не найдена", 404)

    data = request.get_json(silent=True) or {}

    if "name_ru" in data:

        name = data["name_ru"].strip()

        if not name:
            return error("Название категории пустое")

        slug = slugify(name)

        exists = (
            Category.query
            .filter(
                Category.slug == slug,
                Category.id != category.id
            )
            .first()
        )

        if exists:
            return error("Такая категория уже существует")

        category.name_ru = name
        category.slug = slug

    if "name_en" in data:
        category.name_en = data["name_en"].strip()

    if "name_kg" in data:
        category.name_kg = data["name_kg"].strip()

    if "sort_order" in data:
        category.sort_order = int(data["sort_order"])

    if "show_on_main" in data:
        category.show_on_main = bool(data["show_on_main"])

    db.session.commit()

    return success(category_to_dict(category))


@admin_bp.delete("/categories/<int:category_id>")
@login_required
def delete_category(category_id):

    admin = require_admin()
    if admin:
        return admin

    category = db.session.get(Category, category_id)

    if category is None:
        return error("Категория не найдена", 404)

    if category.products:
        return error(
            "Нельзя удалить категорию, пока в ней есть товары",
            409
        )

    db.session.delete(category)
    db.session.commit()

    return success()


@admin_bp.post("/categories/<int:category_id>/image")
@login_required
def upload_category_image(category_id):

    admin = require_admin()
    if admin:
        return admin

    category = db.session.get(Category, category_id)

    if category is None:
        return error("Категория не найдена", 404)

    image = request.files.get("image")

    if image is None:
        return error("Изображение не выбрано")

    try:

        category.image_path = save_image(
            image,
            "categories"
        )

        db.session.commit()

        return success({
            "imageUrl": build_upload_url(
                category.image_path
            )
        })

    except Exception as e:

        db.session.rollback()

        return error(str(e))


@admin_bp.get("/products")
@login_required
def get_products():
    lang = request.args.get("lang", "ru")
    products = Product.query.order_by(Product.sort_order.asc(), Product.id.desc()).all()
    return jsonify([product_to_dict(item, lang) for item in products])


@admin_bp.post("/products")
@login_required
def create_product():

    admin = require_admin()
    if admin:
        return admin

    data = request.get_json(silent=True) or {}

    title = data.get("title_ru", "").strip()

    if not title:
        return error("Введите название товара")

    slug = slugify(title)

    if Product.query.filter_by(slug=slug).first():
        return error("Товар с таким названием уже существует")

    code = data.get("code", "").strip()

    if code:

        if Product.query.filter_by(code=code).first():
            return error("Артикул уже существует")

    category_id = data.get("category_id")

    if category_id:

        category = db.session.get(Category, category_id)

        if category is None:
            return error("Категория не найдена", 404)

    try:

        price = float(data.get("price", 0))

    except:

        return error("Некорректная цена")

    if price < 0:
        return error("Цена не может быть отрицательной")

    product = Product(

        title_ru=title,
        title_en=data.get("title_en", "").strip(),
        title_kg=data.get("title_kg", "").strip(),

        slug=slug,

        code=code,

        description_ru=data.get("description_ru", "").strip(),
        description_en=data.get("description_en", "").strip(),
        description_kg=data.get("description_kg", "").strip(),

        price=price,

        unit=data.get("unit", "шт").strip(),

        in_stock=bool(data.get("in_stock", True)),
        is_popular=bool(data.get("is_popular", False)),

        sort_order=max(
            0,
            int(data.get("sort_order", 0))
        ),

        category_id=category_id,

        extra_images=json.dumps(
            data.get("extra_images", []),
            ensure_ascii=False
        )
    )

    db.session.add(product)
    db.session.commit()

    return success(
        product_to_dict(product),
        201
    )


@admin_bp.put("/products/<int:product_id>")
@login_required
def update_product(product_id):

    admin = require_admin()
    if admin:
        return admin

    product = db.session.get(Product, product_id)

    if product is None:
        return error("Товар не найден", 404)

    data = request.get_json(silent=True) or {}

    if "title_ru" in data:

        title = data["title_ru"].strip()

        if not title:
            return error("Название товара пустое")

        slug = slugify(title)

        exists = (
            Product.query
            .filter(
                Product.slug == slug,
                Product.id != product.id
            )
            .first()
        )

        if exists:
            return error("Такой товар уже существует")

        product.title_ru = title
        product.slug = slug

    if "title_en" in data:
        product.title_en = data["title_en"].strip()

    if "title_kg" in data:
        product.title_kg = data["title_kg"].strip()

    if "code" in data:

        code = data["code"].strip()

        if code:

            exists = (
                Product.query
                .filter(
                    Product.code == code,
                    Product.id != product.id
                )
                .first()
            )

            if exists:
                return error("Такой артикул уже существует")

        product.code = code

    if "description_ru" in data:
        product.description_ru = data["description_ru"]

    if "description_en" in data:
        product.description_en = data["description_en"]

    if "description_kg" in data:
        product.description_kg = data["description_kg"]

    if "price" in data:

        price = float(data["price"])

        if price < 0:
            return error("Цена не может быть отрицательной")

        product.price = price

    if "unit" in data:
        product.unit = data["unit"]

    if "in_stock" in data:
        product.in_stock = bool(data["in_stock"])

    if "is_popular" in data:
        product.is_popular = bool(data["is_popular"])

    if "sort_order" in data:
        product.sort_order = max(0, int(data["sort_order"]))

    if "category_id" in data:

        category_id = data["category_id"]

        if category_id:

            category = db.session.get(Category, category_id)

            if category is None:
                return error("Категория не найдена", 404)

        product.category_id = category_id

    if "extra_images" in data:

        product.extra_images = json.dumps(
            data["extra_images"],
            ensure_ascii=False
        )

    db.session.commit()

    return success(
        product_to_dict(product)
    )


@admin_bp.delete("/products/<int:product_id>")
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    db.session.delete(product)
    db.session.commit()

    return jsonify({
        "success": True
    })


@admin_bp.post("/products/<int:product_id>/image")
@login_required
def upload_product_image(product_id):
    product = Product.query.get_or_404(product_id)

    if "image" not in request.files:
        return jsonify({
            "success": False,
            "error": "Файл не передан"
        }), 400

    try:
        image_path = save_image(request.files["image"], "products")
        product.image_path = image_path
        db.session.commit()

        return jsonify({
            "success": True,
            "imageUrl": build_upload_url(image_path)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@admin_bp.get("/banners")
@login_required
def get_banners():
    lang = request.args.get("lang", "ru")

    banners = Banner.query.order_by(
        Banner.sort_order.asc(),
        Banner.id.desc()
    ).all()

    return jsonify([
        banner_to_dict(item, lang)
        for item in banners
    ])


@admin_bp.post("/banners")
@login_required
def create_banner():
    data = request.get_json(silent=True) or {}

    title_ru = (data.get("title_ru") or "").strip()

    if not title_ru:
        return jsonify({
            "success": False,
            "error": "Введите заголовок баннера"
        }), 400

    banner = Banner(
        title_ru=title_ru,
        title_en=(data.get("title_en") or "").strip(),
        title_kg=(data.get("title_kg") or "").strip(),
        subtitle_ru=(data.get("subtitle_ru") or "").strip(),
        subtitle_en=(data.get("subtitle_en") or "").strip(),
        subtitle_kg=(data.get("subtitle_kg") or "").strip(),
        cta_ru=(data.get("cta_ru") or "Подробнее").strip(),
        cta_en=(data.get("cta_en") or "").strip(),
        cta_kg=(data.get("cta_kg") or "").strip(),
        sort_order=int(data.get("sort_order") or 0),
        active=bool(data.get("active", True))
    )

    db.session.add(banner)
    db.session.commit()

    return jsonify({
        "success": True,
        "item": banner_to_dict(banner)
    }), 201


@admin_bp.put("/banners/<int:banner_id>")
@login_required
def update_banner(banner_id):
    banner = Banner.query.get_or_404(banner_id)

    data = request.get_json(silent=True) or {}

    fields = (
        "title_ru",
        "title_en",
        "title_kg",
        "subtitle_ru",
        "subtitle_en",
        "subtitle_kg",
        "cta_ru",
        "cta_en",
        "cta_kg"
    )

    for field in fields:
        if field in data:
            setattr(
                banner,
                field,
                (data[field] or "").strip()
            )

    if "sort_order" in data:
        banner.sort_order = int(data["sort_order"] or 0)

    if "active" in data:
        banner.active = bool(data["active"])

    db.session.commit()

    return jsonify({
        "success": True,
        "item": banner_to_dict(banner)
    })


@admin_bp.delete("/banners/<int:banner_id>")
@login_required
def delete_banner(banner_id):
    banner = Banner.query.get_or_404(banner_id)

    db.session.delete(banner)
    db.session.commit()

    return jsonify({
        "success": True
    })


@admin_bp.post("/banners/<int:banner_id>/image")
@login_required
def upload_banner_image(banner_id):
    banner = Banner.query.get_or_404(banner_id)

    if "image" not in request.files:
        return jsonify({
            "success": False,
            "error": "Файл не передан"
        }), 400

    try:
        image_path = save_image(
            request.files["image"],
            "banners"
        )

        banner.image_path = image_path

        db.session.commit()

        return jsonify({
            "success": True,
            "imageUrl": build_upload_url(image_path)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@admin_bp.get("/settings")
@login_required
def get_settings():
    lang = request.args.get("lang", "ru")

    settings = SiteSettings.get_singleton()

    return jsonify(
        settings_to_dict(settings, lang)
    )


@admin_bp.put("/settings")
@login_required
def update_settings():
    settings = SiteSettings.get_singleton()

    data = request.get_json(silent=True) or {}

    fields = (
        "company_name",
        "phone_primary",
        "phone_secondary",
        "address_ru",
        "address_en",
        "address_kg",
        "whatsapp",
        "instagram",
        "footer_about_ru",
        "footer_about_en",
        "footer_about_kg",
        "footer_copyright",
    )

    for field in fields:
        if field in data:
            value = data[field]

            if isinstance(value, str):
                value = value.strip()

            setattr(settings, field, value)

    db.session.commit()

    return jsonify({
        "success": True,
        "item": settings_to_dict(settings)
    })


@admin_bp.post("/settings/logo")
@login_required
def upload_logo():
    settings = SiteSettings.get_singleton()

    if "logo" not in request.files:
        return jsonify({
            "success": False,
            "error": "Файл не передан"
        }), 400

    try:
        image_path = save_image(
            request.files["logo"],
            "site"
        )

        settings.logo_path = image_path

        db.session.commit()

        return jsonify({
            "success": True,
            "logoUrl": build_upload_url(image_path)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400