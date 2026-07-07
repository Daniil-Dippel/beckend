import json

from sqlalchemy.orm import joinedload

from .models import Banner, Category, Product, SiteSettings
from .utils import build_upload_url


def parse_images(value):
    if not value:
        return []

    if isinstance(value, list):
        return value

    try:
        data = json.loads(value)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def product_to_dict(product, lang="ru"):
    category = product.category

    return {
        "id": product.id,

        "title": product.get_title(lang),
        "title_ru": product.title_ru,
        "title_en": product.title_en,
        "title_kg": product.title_kg,

        "slug": product.slug,
        "code": product.code or "",

        "description": product.get_description(lang),
        "description_ru": product.description_ru,
        "description_en": product.description_en,
        "description_kg": product.description_kg,

        "price": float(product.price or 0),
        "unit": product.unit,

        "inStock": bool(product.in_stock),
        "isPopular": bool(product.is_popular),

        "sortOrder": product.sort_order,

        "imageUrl": build_upload_url(product.image_path),

        "extraImages": [
            build_upload_url(img)
            for img in parse_images(product.extra_images)
        ],

        "categoryId": product.category_id,
        "categoryName": category.get_name(lang) if category else "",
    }


def category_to_dict(category, lang="ru"):
    return {
        "id": category.id,

        "name": category.get_name(lang),

        "name_ru": category.name_ru,
        "name_en": category.name_en,
        "name_kg": category.name_kg,

        "slug": category.slug,

        "imageUrl": build_upload_url(category.image_path),

        "showOnMain": bool(category.show_on_main),
        "sortOrder": category.sort_order,
    }


def banner_to_dict(banner, lang="ru"):
    return {
        "id": banner.id,

        "title": banner.get_title(lang),
        "title_ru": banner.title_ru,
        "title_en": banner.title_en,
        "title_kg": banner.title_kg,

        "subtitle": banner.get_subtitle(lang),
        "subtitle_ru": banner.subtitle_ru,
        "subtitle_en": banner.subtitle_en,
        "subtitle_kg": banner.subtitle_kg,

        "cta": banner.get_cta(lang),
        "cta_ru": banner.cta_ru,
        "cta_en": banner.cta_en,
        "cta_kg": banner.cta_kg,

        "imageUrl": build_upload_url(banner.image_path),

        "sortOrder": banner.sort_order,
        "active": bool(banner.active),
    }


def settings_to_dict(settings, lang="ru"):
    return {
        "companyName": settings.company_name,

        "logoUrl": build_upload_url(settings.logo_path),

        "phonePrimary": settings.phone_primary,
        "phoneSecondary": settings.phone_secondary,

        "address": settings.get_address(lang),
        "address_ru": settings.address_ru,
        "address_en": settings.address_en,
        "address_kg": settings.address_kg,

        "whatsapp": settings.whatsapp,
        "instagram": settings.instagram,

        "footerAbout": settings.get_footer_about(lang),
        "footerAboutRu": settings.footer_about_ru,
        "footerAboutEn": settings.footer_about_en,
        "footerAboutKg": settings.footer_about_kg,

        "footerCopyright": settings.footer_copyright,
    }


def build_home_payload(lang="ru"):
    settings = SiteSettings.get_singleton()

    banners = (
        Banner.query
        .filter_by(active=True)
        .order_by(Banner.sort_order.asc())
        .all()
    )

    categories = (
        Category.query
        .order_by(Category.sort_order.asc())
        .all()
    )

    popular = (
        Product.query
        .options(joinedload(Product.category))
        .filter_by(
            in_stock=True,
            is_popular=True
        )
        .order_by(Product.sort_order.asc())
        .all()
    )

    if len(popular) < 4:

        ids = {p.id for p in popular}

        extra = (
            Product.query
            .options(joinedload(Product.category))
            .filter_by(in_stock=True)
            .order_by(Product.sort_order.asc())
            .all()
        )

        for product in extra:
            if product.id not in ids:
                popular.append(product)
                ids.add(product.id)

            if len(popular) == 4:
                break

    return {
        "settings": settings_to_dict(settings, lang),

        "banners": [
            banner_to_dict(item, lang)
            for item in banners
        ],

        "categories": [
            category_to_dict(item, lang)
            for item in categories
        ],

        "popularProducts": [
            product_to_dict(item, lang)
            for item in popular
        ],
    }