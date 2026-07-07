import re
import uuid
from pathlib import Path

from flask import current_app, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "sch", "ъ": "", "ы": "y",
    "ь": "", "э": "e", "ю": "yu", "я": "ya"
}


def slugify(value: str) -> str:
    value = (value or "").strip().lower()

    result = []

    for ch in value:
        if ch in TRANSLIT:
            result.append(TRANSLIT[ch])
        else:
            result.append(ch)

    value = "".join(result)

    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)

    value = value.strip("-")

    return value or "item"


def ensure_runtime_dirs(app):
    folders = [
        Path(app.instance_path),
        Path(app.config["UPLOAD_FOLDER"]),
        Path(app.config["UPLOAD_FOLDER"]) / "products",
        Path(app.config["UPLOAD_FOLDER"]) / "categories",
        Path(app.config["UPLOAD_FOLDER"]) / "banners",
        Path(app.config["UPLOAD_FOLDER"]) / "site",
    ]

    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)


def allowed_image(filename: str) -> bool:
    if "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()

    return ext in ALLOWED_IMAGE_EXTENSIONS


def optimize_image(path: Path):
    image = Image.open(path)

    image = ImageOps.exif_transpose(image)

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)

    suffix = path.suffix.lower()

    if suffix in (".jpg", ".jpeg"):
        image.save(
            path,
            quality=90,
            optimize=True
        )

    elif suffix == ".webp":
        image.save(
            path,
            quality=90,
            method=6
        )

    else:
        image.save(path)


def save_image(file_storage, subdir: str) -> str:
    if file_storage is None:
        return ""

    if file_storage.filename == "":
        return ""

    filename = secure_filename(file_storage.filename)

    if not allowed_image(filename):
        raise ValueError("unsupported_image_type")

    try:
        Image.open(file_storage.stream).verify()
    except UnidentifiedImageError:
        raise ValueError("invalid_image")

    file_storage.stream.seek(0)

    extension = filename.rsplit(".", 1)[1].lower()

    filename = f"{uuid.uuid4().hex}.{extension}"

    folder = Path(current_app.config["UPLOAD_FOLDER"]) / subdir
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / filename

    file_storage.save(path)

    try:
        optimize_image(path)
    except Exception:
        pass

    return f"{subdir}/{filename}"


def delete_image(relative_path: str):
    if not relative_path:
        return

    path = Path(current_app.config["UPLOAD_FOLDER"]) / relative_path

    if path.exists():
        path.unlink()


def build_upload_url(relative_path: str) -> str:
    if not relative_path:
        return ""

    return url_for(
        "uploads",
        filename=relative_path.replace("\\", "/"),
        _external=True
    )