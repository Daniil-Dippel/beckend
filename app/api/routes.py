from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..models import Banner, Category, Product, SiteSettings
from ..services import (
    banner_to_dict,
    build_home_payload,
    category_to_dict,
    product_to_dict,
    settings_to_dict,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def get_lang():
    lang = request.args.get("lang", "ru").lower()
    return lang if lang in ("ru", "en", "kg") else "ru"


@api_bp.get("/home")
def home():
    return jsonify(build_home_payload(get_lang()))


@api_bp.get("/categories")
def categories():
    lang = get_lang()

    categories = (
        Category.query
        .order_by(Category.sort_order.asc())
        .all()
    )

    return jsonify([
        category_to_dict(category, lang)
        for category in categories
    ])


@api_bp.get("/categories/<string:slug>/products")
def category_products(slug):
    lang = get_lang()

    category = Category.query.filter_by(slug=slug).first_or_404()

    products = (
        Product.query
        .options(joinedload(Product.category))
        .filter_by(category_id=category.id)
        .order_by(Product.sort_order.asc())
        .all()
    )

    return jsonify([
        product_to_dict(product, lang)
        for product in products
    ])


@api_bp.get("/products")
def products():
    lang = get_lang()

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    category = request.args.get("category")
    in_stock = request.args.get("in_stock")
    popular = request.args.get("popular")

    query = Product.query.options(joinedload(Product.category))

    if category:
        query = query.join(Category).filter(Category.slug == category)

    if in_stock == "1":
        query = query.filter(Product.in_stock.is_(True))

    if popular == "1":
        query = query.filter(Product.is_popular.is_(True))

    pagination = (
        query
        .order_by(Product.sort_order.asc(), Product.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "items": [
            product_to_dict(item, lang)
            for item in pagination.items
        ],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "perPage": pagination.per_page,
        "hasNext": pagination.has_next,
        "hasPrev": pagination.has_prev
    })


@api_bp.get("/products/<string:slug>")
def product_detail(slug):
    lang = get_lang()

    product = (
        Product.query
        .options(joinedload(Product.category))
        .filter_by(slug=slug)
        .first_or_404()
    )

    return jsonify(product_to_dict(product, lang))


@api_bp.get("/products/search")
def search_products():
    lang = get_lang()

    query = request.args.get("q", "").strip()

    if len(query) < 2:
        return jsonify([])

    products = (
        Product.query
        .options(joinedload(Product.category))
        .filter(
            or_(
                Product.title_ru.ilike(f"%{query}%"),
                Product.title_en.ilike(f"%{query}%"),
                Product.title_kg.ilike(f"%{query}%"),
                Product.description_ru.ilike(f"%{query}%"),
                Product.description_en.ilike(f"%{query}%"),
                Product.description_kg.ilike(f"%{query}%"),
                Product.code.ilike(f"%{query}%")
            )
        )
        .order_by(Product.sort_order.asc())
        .limit(20)
        .all()
    )

    return jsonify([
        product_to_dict(product, lang)
        for product in products
    ])


@api_bp.get("/settings")
def settings():
    settings = SiteSettings.get_singleton()
    return jsonify(settings_to_dict(settings, get_lang()))


@api_bp.get("/banners")
def banners():
    lang = get_lang()

    banners = (
        Banner.query
        .filter_by(active=True)
        .order_by(Banner.sort_order.asc())
        .all()
    )

    return jsonify([
        banner_to_dict(item, lang)
        for item in banners
    ])


@api_bp.errorhandler(404)
def not_found(_):
    return jsonify({
        "success": False,
        "error": "Not Found"
    }), 404


@api_bp.errorhandler(400)
def bad_request(_):
    return jsonify({
        "success": False,
        "error": "Bad Request"
    }), 400


@api_bp.errorhandler(500)
def server_error(_):
    return jsonify({
        "success": False,
        "error": "Internal Server Error"
    }), 500