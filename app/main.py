from __future__ import annotations

import base64
from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import Environment, select_autoescape
from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, scoped_session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UPLOAD_DIR = ROOT / "uploads"
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))
SESSION_COOKIE_NAME = "manas_session"
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
TEMPLATES = Environment(autoescape=select_autoescape(["html", "xml"]))


def load_dotenv_file(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


load_dotenv_file()


class Base(DeclarativeBase):
    pass


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    deal: Mapped[str] = mapped_column(String(32), default="sale", nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="apartment", nullable=False)
    price: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    instagram_url: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    cover_image: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    badges_ky_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    badges_ru_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    whatsapp_ky: Mapped[str] = mapped_column(Text, default="", nullable=False)
    whatsapp_ru: Mapped[str] = mapped_column(Text, default="", nullable=False)
    title_ky: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    title_ru: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    location_ky: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    location_ru: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    meta_ky_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    meta_ru_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    description_ky: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_ru: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc(), nullable=False)


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc(), nullable=False)


class SiteSettings(Base):
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    phone_primary: Mapped[str] = mapped_column(String(64), default="0888 001 002", nullable=False)
    phone_secondary: Mapped[str] = mapped_column(String(64), default="0888 002 001", nullable=False)
    whatsapp_phone: Mapped[str] = mapped_column(String(32), default="996888001002", nullable=False)
    instagram_url: Mapped[str] = mapped_column(String(512), default="https://www.instagram.com/jalal_abad__nedvijimost/", nullable=False)
    hero_kicker_ky: Mapped[str] = mapped_column(String(255), default="Манас / Жалал-Абад · текшерилген варианттар", nullable=False)
    hero_kicker_ru: Mapped[str] = mapped_column(String(255), default="Манас / Жалал-Абад · проверенные варианты", nullable=False)
    hero_title_ky: Mapped[str] = mapped_column(String(255), default="Ишенимдүү мүлк тандоо", nullable=False)
    hero_title_ru: Mapped[str] = mapped_column(String(255), default="Недвижимость без лишнего риска", nullable=False)
    hero_lead_ky: Mapped[str] = mapped_column(Text, default="Бюджетти, районду жана максатыңызды жазыңыз — ылайыксыз варианттарга убакыт коротпой, сизге туура келген объекттерди тандап беребиз.", nullable=False)
    hero_lead_ru: Mapped[str] = mapped_column(Text, default="Напишите бюджет, район и цель — уберём лишние варианты и предложим объекты, которые действительно стоит смотреть.", nullable=False)
    cta_text_ky: Mapped[str] = mapped_column(String(128), default="Варианттарды алуу", nullable=False)
    cta_text_ru: Mapped[str] = mapped_column(String(128), default="Получить варианты", nullable=False)
    seo_title_ky: Mapped[str] = mapped_column(String(255), default="Манас / Жалал-Абад кыймылсыз мүлк | Manas Estate", nullable=False)
    seo_title_ru: Mapped[str] = mapped_column(String(255), default="Недвижимость Манас / Жалал-Абад | Manas Estate", nullable=False)
    seo_description_ky: Mapped[str] = mapped_column(Text, default="Манас жана Жалал-Абад боюнча кыймылсыз мүлк: батир, үй, жер тилкеси жана коммерция. Бюджетиңизге ылайык вариант таап, көрүүгө чейин коштоп беребиз.", nullable=False)
    seo_description_ru: Mapped[str] = mapped_column(Text, default="Недвижимость в Манасе и Жалал-Абаде: квартиры, дома, участки и коммерция. Подберём варианты под бюджет и поможем дойти до просмотра.", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc(), nullable=False)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_database_url(raw: str) -> str:
    value = raw or f"sqlite:///{ROOT / 'data' / 'manas.db'}"
    if value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql+psycopg://", 1)
    elif value.startswith("postgresql://") and "+" not in value.split("://", 1)[0]:
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


def env_truthy(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_config_value(test_config: dict[str, Any] | None, key: str, default: Any = "") -> Any:
    if test_config and key in test_config:
        return test_config[key]
    return os.environ.get(key, default)


def validate_runtime_config(test_config: dict[str, Any] | None, database_url: str, secret_key: str, admin_password_hash: str) -> bool:
    testing = bool(test_config and test_config.get("TESTING"))
    raw_allow_insecure = get_config_value(test_config, "ALLOW_INSECURE_DEV_AUTH", "")
    if isinstance(raw_allow_insecure, bool):
        configured_allow_insecure = raw_allow_insecure
    else:
        configured_allow_insecure = str(raw_allow_insecure).strip().lower() in {"1", "true", "yes", "on"}
    allow_insecure_dev_auth = testing or configured_allow_insecure or env_truthy("ALLOW_INSECURE_DEV_AUTH")
    app_env = str(get_config_value(test_config, "APP_ENV", os.environ.get("FASTAPI_ENV", os.environ.get("FLASK_ENV", ""))) or "").lower()
    render_runtime = any(os.environ.get(name) for name in ("RENDER", "RENDER_SERVICE_ID", "RENDER_EXTERNAL_URL"))
    production = app_env in {"production", "prod"} or render_runtime
    explicit_dev = app_env in {"development", "dev", "local"} or allow_insecure_dev_auth

    weak_secret = not secret_key or secret_key in {"dev-only-change-me", "change-me-in-render"} or len(secret_key) < 32
    if production:
        if database_url.startswith("sqlite:///"):
            raise RuntimeError("DATABASE_URL must point to Render Postgres in production")
        if weak_secret:
            raise RuntimeError("SECRET_KEY must be a strong production secret")
        if not admin_password_hash:
            raise RuntimeError("ADMIN_PASSWORD_HASH is required in production")
    elif not explicit_dev and not admin_password_hash:
        raise RuntimeError("Set ADMIN_PASSWORD_HASH or ALLOW_INSECURE_DEV_AUTH=1 for local development")

    return allow_insecure_dev_auth


def json_list(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(split_list(value), ensure_ascii=False)
    if isinstance(value, list):
        return json.dumps([str(item).strip() for item in value if str(item).strip()], ensure_ascii=False)
    return "[]"


def load_json_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed if str(item)] if isinstance(parsed, list) else []


def split_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[;,|]", str(value or "")) if item.strip()]


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁүҮңҢөӨ\s-]", "", value or "listing")
    cleaned = re.sub(r"\s+", "-", cleaned.strip().lower()).strip("-")
    return cleaned[:64] or f"listing-{uuid.uuid4().hex[:8]}"


def is_safe_instagram_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return ""
    host = (parsed.hostname or "").removeprefix("www.")
    return candidate if parsed.scheme == "https" and host == "instagram.com" else ""


def deal_label(deal: str, lang: str) -> str:
    labels = {
        "sale": {"ky": "Сатуу", "ru": "Продажа"},
        "rent": {"ky": "Ижара", "ru": "Аренда"},
        "buyout": {"ky": "Тез сатып алуу", "ru": "Срочный выкуп"},
    }
    return labels.get(deal, {"ky": deal or "Объект", "ru": deal or "Объект"})[lang]


def category_label(category: str, lang: str) -> str:
    labels = {
        "apartment": {"ky": "Батир", "ru": "Квартира"},
        "house": {"ky": "Үй", "ru": "Дом"},
        "land": {"ky": "Жер", "ru": "Участок"},
        "commercial": {"ky": "Коммерция", "ru": "Коммерция"},
    }
    return labels.get(category, {"ky": category or "Объект", "ru": category or "Объект"})[lang]


def generate_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${base64.urlsafe_b64encode(digest).decode('ascii')}"


def check_password_hash(password_hash: str, password: str) -> bool:
    if password_hash.startswith("pbkdf2_sha256$"):
        return check_local_password_hash(password_hash, password)
    if password_hash.startswith(("pbkdf2:", "scrypt:")):
        return check_werkzeug_password_hash(password_hash, password)
    return False


def check_local_password_hash(password_hash: str, password: str) -> bool:
    try:
        algorithm, iterations_raw, salt, digest_raw = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        expected = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(expected, actual)


def check_werkzeug_password_hash(password_hash: str, password: str) -> bool:
    try:
        method, salt, expected_hex = password_hash.split("$", 2)
        password_bytes = password.encode("utf-8")
        salt_bytes = salt.encode("utf-8")
        if method.startswith("pbkdf2:"):
            _, hash_name, iterations_raw = method.split(":", 2)
            actual_hex = hashlib.pbkdf2_hmac(hash_name, password_bytes, salt_bytes, int(iterations_raw)).hex()
        elif method.startswith("scrypt:"):
            _, n_raw, r_raw, p_raw = method.split(":", 3)
            n, r, p = int(n_raw), int(r_raw), int(p_raw)
            actual_hex = hashlib.scrypt(password_bytes, salt=salt_bytes, n=n, r=r, p=p, maxmem=132 * n * r * p, dklen=64).hex()
        else:
            return False
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(expected_hex, actual_hex)


def create_app(test_config: dict[str, Any] | None = None) -> FastAPI:
    database_url = normalize_database_url(str(get_config_value(test_config, "DATABASE_URL", "")))
    upload_dir = Path(str(get_config_value(test_config, "UPLOAD_DIR", str(DEFAULT_UPLOAD_DIR)))).resolve()
    secret_key = str(get_config_value(test_config, "SECRET_KEY", "dev-only-change-me"))
    admin_password_hash = str(get_config_value(test_config, "ADMIN_PASSWORD_HASH", ""))
    allow_insecure_dev_auth = validate_runtime_config(test_config, database_url, secret_key, admin_password_hash)

    config = {
        "TESTING": bool(test_config and test_config.get("TESTING")),
        "SECRET_KEY": secret_key,
        "DATABASE_URL": database_url,
        "UPLOAD_DIR": upload_dir,
        "ADMIN_USERNAME": str(get_config_value(test_config, "ADMIN_USERNAME", "admin")),
        "ADMIN_PASSWORD_HASH": admin_password_hash,
        "ALLOW_INSECURE_DEV_AUTH": allow_insecure_dev_auth,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "lax",
        "PERMANENT_SESSION_LIFETIME": SESSION_MAX_AGE_SECONDS,
    }
    if test_config:
        config.update(test_config)

    upload_dir.mkdir(parents=True, exist_ok=True)
    if database_url.startswith("sqlite:///"):
        Path(database_url.replace("sqlite:///", "", 1)).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}

    engine = create_engine(database_url, future=True, connect_args=connect_args)
    db_session = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            db_session.remove()

    app = FastAPI(title="Manas Estate Admin Backend", lifespan=lifespan)
    app.state.config = config
    app.state.engine = engine
    app.state.db_session = db_session
    app.config = config  # type: ignore[attr-defined]
    app.engine = engine  # type: ignore[attr-defined]
    app.db_session = db_session  # type: ignore[attr-defined]

    init_db(app)

    @app.get("/")
    def home():
        return FileResponse(ROOT / "index.html")

    @app.get("/catalog.json")
    def legacy_catalog():
        return FileResponse(ROOT / "catalog.json")

    @app.get("/uploads/{filename:path}")
    def uploaded_file(filename: str):
        return upload_file_response(app, filename)

    @app.get("/health")
    def health():
        ok = True
        try:
            db_session.execute(text("SELECT 1"))
        except Exception:
            ok = False
        return JSONResponse({"ok": ok, "database": "ok" if ok else "error"}, status_code=200 if ok else 503)

    @app.get("/api/listings")
    def api_listings():
        rows = db_session.scalars(select(Listing).where(Listing.published.is_(True)).order_by(Listing.sort, Listing.id)).all()
        return {"listings": [public_listing_dict(item) for item in rows]}

    @app.get("/api/site-settings")
    def api_site_settings():
        return site_settings_payload(get_site_settings(app))

    @app.get("/admin/login")
    def admin_login_form(request: Request):
        return render_template(request, LOGIN_TEMPLATE)

    @app.post("/admin/login")
    async def admin_login(request: Request):
        form = await request.form()
        validate_csrf(request, form)
        username = form_value(form, "username").strip()
        password = form_value(form, "password")
        if username == app.state.config["ADMIN_USERNAME"] and check_admin_password(app, password):
            data = {"admin": True, "_csrf_token": secrets.token_urlsafe(32)}
            response = RedirectResponse("/admin", status_code=303)
            commit_session(response, request, data)
            return response
        return render_template(request, LOGIN_TEMPLATE, messages=["Неверный логин или пароль"])

    @app.post("/admin/logout")
    async def admin_logout(request: Request):
        form = await request.form()
        validate_csrf(request, form)
        response = RedirectResponse("/admin/login", status_code=303)
        clear_session(response)
        return response

    @app.get("/admin")
    def admin_dashboard(request: Request):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        listings = db_session.scalars(select(Listing).order_by(Listing.sort, Listing.id)).all()
        return render_template(request, ADMIN_LIST_TEMPLATE, listings=listings, load_json_list=load_json_list)

    @app.get("/admin/settings")
    def admin_settings_form(request: Request):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        return render_template(request, ADMIN_SETTINGS_TEMPLATE, settings=get_site_settings(app))

    @app.post("/admin/settings")
    async def admin_settings_save(request: Request):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        form = await request.form()
        validate_csrf(request, form)
        settings = get_site_settings(app)
        apply_site_settings_form(form, settings)
        db_session.commit()
        return redirect_with_flash(request, "/admin/settings", "Настройки сохранены")

    @app.get("/admin/listings/new")
    def admin_listing_new_form(request: Request):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        return render_template(request, ADMIN_FORM_TEMPLATE, listing=Listing(published=True, sort=100), action="/admin/listings/new", is_new=True, load_json_list=load_json_list)

    @app.post("/admin/listings/new")
    async def admin_listing_new(request: Request):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        form = await request.form()
        validate_csrf(request, form)
        listing = Listing(id=slugify(form_value(form, "id") or form_value(form, "title_ru") or form_value(form, "title_ky") or "listing"))
        await apply_listing_form(app, form, listing)
        existing = db_session.get(Listing, listing.id)
        if existing:
            flash(request, "ID уже существует — откройте объект для редактирования")
            return render_template(request, ADMIN_FORM_TEMPLATE, listing=listing, action="/admin/listings/new", is_new=True, load_json_list=load_json_list)
        db_session.add(listing)
        db_session.commit()
        return redirect_with_flash(request, "/admin", "Объект создан")

    @app.get("/admin/listings/{listing_id}/edit")
    def admin_listing_edit_form(request: Request, listing_id: str):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        listing = db_session.get(Listing, listing_id)
        if not listing:
            raise HTTPException(status_code=404)
        return render_template(request, ADMIN_FORM_TEMPLATE, listing=listing, action=f"/admin/listings/{listing.id}/edit", is_new=False, load_json_list=load_json_list)

    @app.post("/admin/listings/{listing_id}/edit")
    async def admin_listing_edit(request: Request, listing_id: str):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        listing = db_session.get(Listing, listing_id)
        if not listing:
            raise HTTPException(status_code=404)
        form = await request.form()
        validate_csrf(request, form)
        await apply_listing_form(app, form, listing)
        listing.updated_at = now_utc()
        db_session.commit()
        return redirect_with_flash(request, "/admin", "Объект обновлён")

    @app.post("/admin/listings/{listing_id}/delete-cover")
    async def admin_delete_cover(request: Request, listing_id: str):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        form = await request.form()
        validate_csrf(request, form)
        listing = db_session.get(Listing, listing_id)
        if not listing:
            raise HTTPException(status_code=404)
        delete_cover_file(app, listing.cover_image)
        listing.cover_image = ""
        listing.updated_at = now_utc()
        db_session.commit()
        return redirect_with_flash(request, f"/admin/listings/{listing.id}/edit", "Cover-фото удалено")

    @app.post("/admin/listings/{listing_id}/delete")
    async def admin_listing_delete(request: Request, listing_id: str):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        form = await request.form()
        validate_csrf(request, form)
        listing = db_session.get(Listing, listing_id)
        if not listing:
            raise HTTPException(status_code=404)
        delete_cover_file(app, listing.cover_image)
        db_session.delete(listing)
        db_session.commit()
        return redirect_with_flash(request, "/admin", "Объект удалён")

    @app.post("/admin/import")
    async def admin_import(request: Request):
        unauthorized = admin_redirect_if_needed(request)
        if unauthorized:
            return unauthorized
        form = await request.form()
        validate_csrf(request, form)
        existing_import = db_session.scalars(select(ImportRun).order_by(ImportRun.created_at.desc())).first()
        if existing_import and form_value(form, "confirm_import").strip() != "IMPORT":
            return redirect_with_flash(request, "/admin", "Импорт catalog.json уже выполнялся. Для повторного обновления впишите IMPORT в поле подтверждения.")
        result = import_catalog(app, ROOT / "catalog.json")
        return redirect_with_flash(request, "/admin", f"Импорт: создано {result['created']}, обновлено {result['updated']}, пропущено {result['skipped']}")

    return app


def init_db(app: FastAPI) -> None:
    Base.metadata.create_all(app.state.engine)


def b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def signed_session_value(secret_key: str, data: dict[str, Any]) -> str:
    body = b64encode(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def load_signed_session(secret_key: str, value: str | None) -> dict[str, Any]:
    if not value or "." not in value:
        return {}
    body, signature = value.rsplit(".", 1)
    expected = hmac.new(secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return {}
    try:
        data = json.loads(b64decode(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}
    if int(data.get("_expires", 0) or 0) < int(time.time()):
        return {}
    return data if isinstance(data, dict) else {}


def get_session(request: Request) -> dict[str, Any]:
    if not hasattr(request.state, "session_data"):
        secret_key = request.app.state.config["SECRET_KEY"]
        request.state.session_data = load_signed_session(secret_key, request.cookies.get(SESSION_COOKIE_NAME))
    return request.state.session_data


def commit_session(response, request: Request, data: dict[str, Any] | None = None) -> None:
    session_data = get_session(request) if data is None else data
    if not session_data:
        clear_session(response)
        return
    session_data["_expires"] = int(time.time()) + SESSION_MAX_AGE_SECONDS
    value = signed_session_value(request.app.state.config["SECRET_KEY"], session_data)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        value,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )


def clear_session(response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME)


def csrf_token(request: Request) -> str:
    data = get_session(request)
    token = data.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        data["_csrf_token"] = token
    return str(token)


def validate_csrf(request: Request, form) -> None:
    expected = get_session(request).get("_csrf_token")
    submitted = form_value(form, "_csrf_token")
    if not expected or not submitted or not hmac.compare_digest(str(expected), submitted):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")


def flash(request: Request, message: str) -> None:
    data = get_session(request)
    data.setdefault("_flash", []).append(message)


def pop_flash(request: Request) -> list[str]:
    data = get_session(request)
    messages = data.get("_flash") or []
    data["_flash"] = []
    return [str(message) for message in messages]


def route_url_for(name: str, **kwargs) -> str:
    routes = {
        "admin_dashboard": "/admin",
        "admin_login": "/admin/login",
        "admin_logout": "/admin/logout",
        "admin_settings": "/admin/settings",
        "admin_import": "/admin/import",
        "admin_listing_new": "/admin/listings/new",
        "admin_listing_edit": f"/admin/listings/{kwargs.get('listing_id', '')}/edit",
        "admin_listing_delete": f"/admin/listings/{kwargs.get('listing_id', '')}/delete",
        "admin_delete_cover": f"/admin/listings/{kwargs.get('listing_id', '')}/delete-cover",
    }
    return routes[name]


def render_template(request: Request, template_source: str, messages: list[str] | None = None, **context) -> HTMLResponse:
    template = TEMPLATES.from_string(template_source)
    rendered = template.render(
        **context,
        csrf_token=lambda: csrf_token(request),
        url_for=route_url_for,
        get_flashed_messages=lambda: messages if messages is not None else pop_flash(request),
    )
    response = HTMLResponse(rendered)
    commit_session(response, request)
    return response


def admin_redirect_if_needed(request: Request):
    if not get_session(request).get("admin"):
        response = RedirectResponse("/admin/login", status_code=302)
        commit_session(response, request)
        return response
    return None


def redirect_with_flash(request: Request, url: str, message: str):
    flash(request, message)
    response = RedirectResponse(url, status_code=303)
    commit_session(response, request)
    return response


def form_value(form, name: str, default: str = "") -> str:
    value = form.get(name, default)
    return value if isinstance(value, str) else default


def check_admin_password(app: FastAPI, password: str) -> bool:
    password_hash = app.state.config.get("ADMIN_PASSWORD_HASH") or ""
    if password_hash:
        return check_password_hash(password_hash, password)
    if app.state.config.get("ALLOW_INSECURE_DEV_AUTH"):
        return password == os.environ.get("ADMIN_PASSWORD", "admin")
    return False


def detect_image_extension(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return ""


def public_listing_dict(listing: Listing) -> dict[str, Any]:
    tags = load_json_list(listing.tags_json)
    filters = [listing.deal, listing.category, *tags]
    return {
        "id": listing.id,
        "active": listing.published,
        "sort": listing.sort,
        "deal": listing.deal,
        "category": listing.category,
        "filters": [item for item in filters if item],
        "price": listing.price,
        "instagramUrl": listing.instagram_url,
        "coverImageUrl": f"/uploads/{listing.cover_image}" if listing.cover_image else "",
        "whatsapp": {"ky": listing.whatsapp_ky, "ru": listing.whatsapp_ru},
        "badges": {"ky": load_json_list(listing.badges_ky_json), "ru": load_json_list(listing.badges_ru_json)},
        "ky": {"title": listing.title_ky, "location": listing.location_ky, "meta": load_json_list(listing.meta_ky_json), "description": listing.description_ky},
        "ru": {"title": listing.title_ru, "location": listing.location_ru, "meta": load_json_list(listing.meta_ru_json), "description": listing.description_ru},
    }


def normalize_whatsapp_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    return digits or "996888001002"


def get_site_settings(app: FastAPI) -> SiteSettings:
    db = app.state.db_session
    settings = db.get(SiteSettings, 1)
    if settings is None:
        settings = SiteSettings(id=1)
        db.add(settings)
        db.commit()
    return settings


def site_settings_payload(settings: SiteSettings) -> dict[str, Any]:
    phones = [settings.phone_primary.strip(), settings.phone_secondary.strip()]
    return {
        "contacts": {
            "phones": [phone for phone in phones if phone],
            "whatsappPhone": normalize_whatsapp_phone(settings.whatsapp_phone),
            "instagramUrl": is_safe_instagram_url(settings.instagram_url) or "https://www.instagram.com/jalal_abad__nedvijimost/",
        },
        "copy": {
            "ky": {
                "heroKicker": settings.hero_kicker_ky,
                "heroTitle": settings.hero_title_ky,
                "heroLead": settings.hero_lead_ky,
                "ctaText": settings.cta_text_ky,
                "seoTitle": settings.seo_title_ky,
                "seoDescription": settings.seo_description_ky,
            },
            "ru": {
                "heroKicker": settings.hero_kicker_ru,
                "heroTitle": settings.hero_title_ru,
                "heroLead": settings.hero_lead_ru,
                "ctaText": settings.cta_text_ru,
                "seoTitle": settings.seo_title_ru,
                "seoDescription": settings.seo_description_ru,
            },
        },
    }


def apply_site_settings_form(form, settings: SiteSettings) -> None:
    settings.phone_primary = form_value(form, "phone_primary").strip()
    settings.phone_secondary = form_value(form, "phone_secondary").strip()
    settings.whatsapp_phone = normalize_whatsapp_phone(form_value(form, "whatsapp_phone"))
    settings.instagram_url = is_safe_instagram_url(form_value(form, "instagram_url")) or "https://www.instagram.com/jalal_abad__nedvijimost/"
    settings.hero_kicker_ky = form_value(form, "hero_kicker_ky").strip()
    settings.hero_kicker_ru = form_value(form, "hero_kicker_ru").strip()
    settings.hero_title_ky = form_value(form, "hero_title_ky").strip()
    settings.hero_title_ru = form_value(form, "hero_title_ru").strip()
    settings.hero_lead_ky = form_value(form, "hero_lead_ky").strip()
    settings.hero_lead_ru = form_value(form, "hero_lead_ru").strip()
    settings.cta_text_ky = form_value(form, "cta_text_ky").strip()
    settings.cta_text_ru = form_value(form, "cta_text_ru").strip()
    settings.seo_title_ky = form_value(form, "seo_title_ky").strip()
    settings.seo_title_ru = form_value(form, "seo_title_ru").strip()
    settings.seo_description_ky = form_value(form, "seo_description_ky").strip()
    settings.seo_description_ru = form_value(form, "seo_description_ru").strip()
    settings.updated_at = now_utc()


async def apply_listing_form(app: FastAPI, form, listing: Listing) -> None:
    listing.published = form_value(form, "published") == "on"
    listing.sort = int(form_value(form, "sort") or 100)
    listing.deal = form_value(form, "deal", "sale")
    listing.category = form_value(form, "category", "apartment")
    listing.price = form_value(form, "price").strip()
    listing.instagram_url = is_safe_instagram_url(form_value(form, "instagram_url"))
    listing.tags_json = json_list(form_value(form, "tags"))
    listing.badges_ky_json = json_list(form_value(form, "badges_ky"))
    listing.badges_ru_json = json_list(form_value(form, "badges_ru"))
    listing.whatsapp_ky = form_value(form, "whatsapp_ky").strip()
    listing.whatsapp_ru = form_value(form, "whatsapp_ru").strip()
    listing.title_ky = form_value(form, "title_ky").strip()
    listing.title_ru = form_value(form, "title_ru").strip()
    listing.location_ky = form_value(form, "location_ky").strip()
    listing.location_ru = form_value(form, "location_ru").strip()
    listing.meta_ky_json = json_list(form_value(form, "meta_ky"))
    listing.meta_ru_json = json_list(form_value(form, "meta_ru"))
    listing.description_ky = form_value(form, "description_ky").strip()
    listing.description_ru = form_value(form, "description_ru").strip()
    listing.updated_at = now_utc()

    uploaded = form.get("cover_image")
    if uploaded is not None and getattr(uploaded, "filename", ""):
        new_name = await store_cover_file(app, uploaded)
        delete_cover_file(app, listing.cover_image)
        listing.cover_image = new_name


async def store_cover_file(app: FastAPI, uploaded) -> str:
    filename = str(getattr(uploaded, "filename", "") or "cover")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    try:
        data = await uploaded.read()
    finally:
        close = getattr(uploaded, "close", None)
        if close is not None:
            await close()
    if not data:
        raise HTTPException(status_code=400, detail="Image is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large")
    detected_extension = detect_image_extension(data)
    expected_extension = "jpeg" if extension in {"jpg", "jpeg"} else extension
    if detected_extension != expected_extension:
        raise HTTPException(status_code=400, detail="Unsupported image content")
    stored = f"{uuid.uuid4().hex}.{extension}"
    target = Path(app.state.config["UPLOAD_DIR"]) / stored
    target.write_bytes(data)
    return stored


def delete_cover_file(app: FastAPI, filename: str) -> None:
    if not filename:
        return
    target = (Path(app.state.config["UPLOAD_DIR"]) / filename).resolve()
    upload_dir = Path(app.state.config["UPLOAD_DIR"]).resolve()
    if upload_dir in target.parents and target.exists():
        target.unlink()


def upload_file_response(app: FastAPI, filename: str):
    upload_dir = Path(app.state.config["UPLOAD_DIR"]).resolve()
    target = (upload_dir / filename).resolve()
    if upload_dir not in target.parents or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(target)


def import_catalog(app: FastAPI, path: Path) -> dict[str, int]:
    db = app.state.db_session
    catalog = json.loads(path.read_text(encoding="utf-8"))
    stats = {"created": 0, "updated": 0, "skipped": 0}
    for index, item in enumerate(catalog.get("listings", []), start=1):
        listing_id = str(item.get("id") or f"legacy-{index}")
        listing = db.get(Listing, listing_id)
        created = listing is None
        if listing is None:
            listing = Listing(id=listing_id, source="catalog-import")
            db.add(listing)
        update_listing_from_legacy(listing, item, index)
        stats["created" if created else "updated"] += 1
    db.add(ImportRun(source=str(path), **stats))
    db.commit()
    return stats


def update_listing_from_legacy(listing: Listing, item: dict[str, Any], index: int) -> None:
    ky = item.get("ky") or {}
    ru = item.get("ru") or {}
    deal = item.get("deal") or "sale"
    category = item.get("category") or "apartment"
    listing.published = bool(item.get("active", True))
    listing.sort = int(item.get("sort") or index)
    listing.deal = deal
    listing.category = category
    listing.price = str(item.get("price") or "")
    listing.instagram_url = is_safe_instagram_url(item.get("instagramUrl") or item.get("postUrl") or "")
    listing.tags_json = json_list(item.get("filters") or [deal, category])
    badges = item.get("badges") or {}
    listing.badges_ky_json = json_list(badges.get("ky") or [deal_label(deal, "ky"), category_label(category, "ky")])
    listing.badges_ru_json = json_list(badges.get("ru") or [deal_label(deal, "ru"), category_label(category, "ru")])
    whatsapp = item.get("whatsapp") or {}
    listing.whatsapp_ky = str(whatsapp.get("ky") or f"Саламатсызбы! Толугураак билгим келет: {ky.get('title') or ''}.")
    listing.whatsapp_ru = str(whatsapp.get("ru") or f"Здравствуйте! Хочу узнать детали: {ru.get('title') or ''}.")
    listing.title_ky = str(ky.get("title") or category_label(category, "ky"))
    listing.title_ru = str(ru.get("title") or category_label(category, "ru"))
    listing.location_ky = str(ky.get("location") or "")
    listing.location_ru = str(ru.get("location") or "")
    listing.meta_ky_json = json_list(ky.get("meta") or [])
    listing.meta_ru_json = json_list(ru.get("meta") or [])
    listing.description_ky = str(ky.get("description") or "")
    listing.description_ru = str(ru.get("description") or "")
    listing.updated_at = now_utc()


BASE_STYLE = """
<style>
body{margin:0;background:#050505;color:#fff;font-family:Inter,system-ui,sans-serif}.wrap{width:min(1120px,calc(100% - 32px));margin:auto;padding:32px 0}.panel{border:1px solid rgba(255,255,255,.16);background:#101013;padding:18px;margin:14px 0}.top{display:flex;justify-content:space-between;gap:16px;align-items:center}a,.link{color:#cda15a}.button,button{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 14px;border:1px solid #fff;background:transparent;color:#fff;text-decoration:none;font-weight:800;cursor:pointer}.green{background:#12b981;border-color:#12b981;color:#03130d}.red{border-color:#ef4444}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}label{display:grid;gap:6px;font-size:13px;font-weight:800}input,select,textarea{width:100%;box-sizing:border-box;min-height:38px;background:#050506;color:#fff;border:1px solid rgba(255,255,255,.2);padding:9px}textarea{min-height:88px}.muted{color:rgba(255,255,255,.65)}.flash{border:1px solid #12b981;padding:10px;margin:10px 0}.card{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center}@media(max-width:720px){.grid,.card{grid-template-columns:1fr}.top{display:block}}
</style>
"""

LOGIN_TEMPLATE = BASE_STYLE + """
<main class="wrap"><section class="panel" style="max-width:480px"><h1>Manas Estate Admin</h1>
{% for message in get_flashed_messages() %}<div class="flash">{{ message }}</div>{% endfor %}
<form method="post"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><label>Логин <input name="username" autocomplete="username" required></label><label>Пароль <input name="password" type="password" autocomplete="current-password" required></label><p><button class="green" type="submit">Войти</button></p></form>
<p class="muted">Production пароль задаётся через ADMIN_PASSWORD_HASH в Render.</p></section></main>
"""

ADMIN_LIST_TEMPLATE = BASE_STYLE + """
<main class="wrap"><div class="top"><h1>Каталог</h1><form method="post" action="{{ url_for('admin_logout') }}"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><button type="submit">Выйти</button></form></div>
{% for message in get_flashed_messages() %}<div class="flash">{{ message }}</div>{% endfor %}
<div class="top"><a class="button green" href="{{ url_for('admin_listing_new') }}">Новый объект</a><a class="button" href="{{ url_for('admin_settings') }}">Настройки сайта</a></div>
{% for item in listings %}<section class="panel card"><div><strong>{{ item.sort }} · {{ item.title_ru or item.title_ky }}</strong><div class="muted">{{ item.deal }} / {{ item.category }} · {{ 'published' if item.published else 'hidden' }} · {{ item.price }}</div></div><div class="top"><a class="button" href="{{ url_for('admin_listing_edit', listing_id=item.id) }}">Редактировать</a><form method="post" action="{{ url_for('admin_listing_delete', listing_id=item.id) }}"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><button class="red" type="submit">Удалить</button></form></div></section>{% else %}<section class="panel muted">Пока нет объектов. Создайте первый объект вручную.</section>{% endfor %}</main>
"""

ADMIN_SETTINGS_TEMPLATE = BASE_STYLE + """
<main class="wrap"><div class="top"><h1>Настройки сайта</h1><a class="button" href="{{ url_for('admin_dashboard') }}">Назад в каталог</a></div>
{% for message in get_flashed_messages() %}<div class="flash">{{ message }}</div>{% endfor %}
<form class="panel" method="post" action="{{ url_for('admin_settings') }}">
<input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
<h2>Контакты</h2>
<div class="grid"><label>Телефон 1 <input name="phone_primary" value="{{ settings.phone_primary }}"></label><label>Телефон 2 <input name="phone_secondary" value="{{ settings.phone_secondary }}"></label></div>
<div class="grid"><label>WhatsApp номер <input name="whatsapp_phone" value="{{ settings.whatsapp_phone }}" placeholder="996888001002"></label><label>Instagram URL <input name="instagram_url" value="{{ settings.instagram_url }}"></label></div>
<h2>Главный экран KG</h2>
<label>Малый заголовок <input name="hero_kicker_ky" value="{{ settings.hero_kicker_ky }}"></label>
<label>Главный заголовок <input name="hero_title_ky" value="{{ settings.hero_title_ky }}"></label>
<label>Описание <textarea name="hero_lead_ky">{{ settings.hero_lead_ky }}</textarea></label>
<label>Текст CTA <input name="cta_text_ky" value="{{ settings.cta_text_ky }}"></label>
<h2>Главный экран RU</h2>
<label>Малый заголовок <input name="hero_kicker_ru" value="{{ settings.hero_kicker_ru }}"></label>
<label>Главный заголовок <input name="hero_title_ru" value="{{ settings.hero_title_ru }}"></label>
<label>Описание <textarea name="hero_lead_ru">{{ settings.hero_lead_ru }}</textarea></label>
<label>Текст CTA <input name="cta_text_ru" value="{{ settings.cta_text_ru }}"></label>
<h2>SEO</h2>
<div class="grid"><label>SEO title KG <input name="seo_title_ky" value="{{ settings.seo_title_ky }}"></label><label>SEO title RU <input name="seo_title_ru" value="{{ settings.seo_title_ru }}"></label></div>
<div class="grid"><label>SEO description KG <textarea name="seo_description_ky">{{ settings.seo_description_ky }}</textarea></label><label>SEO description RU <textarea name="seo_description_ru">{{ settings.seo_description_ru }}</textarea></label></div>
<p><button class="green" type="submit">Сохранить настройки</button></p>
</form></main>
"""

ADMIN_FORM_TEMPLATE = BASE_STYLE + """
<main class="wrap"><div class="top"><h1>{{ 'Новый объект' if is_new else 'Редактирование' }}</h1><a class="button" href="{{ url_for('admin_dashboard') }}">Назад</a></div>
{% for message in get_flashed_messages() %}<div class="flash">{{ message }}</div>{% endfor %}
<form class="panel" method="post" enctype="multipart/form-data" action="{{ action }}">
<input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
<label><input type="checkbox" name="published" {% if listing.published %}checked{% endif %}> Опубликован</label>
<div class="grid"><label>ID <input name="id" value="{{ listing.id or '' }}" {% if not is_new %}readonly{% endif %}></label><label>Сортировка <input name="sort" type="number" value="{{ listing.sort or 100 }}"></label></div>
<div class="grid"><label>Сделка <select name="deal"><option value="sale" {% if listing.deal=='sale' %}selected{% endif %}>Продажа</option><option value="rent" {% if listing.deal=='rent' %}selected{% endif %}>Аренда</option><option value="buyout" {% if listing.deal=='buyout' %}selected{% endif %}>Выкуп</option></select></label><label>Тип <select name="category"><option value="apartment" {% if listing.category=='apartment' %}selected{% endif %}>Квартира</option><option value="house" {% if listing.category=='house' %}selected{% endif %}>Дом</option><option value="land" {% if listing.category=='land' %}selected{% endif %}>Участок</option><option value="commercial" {% if listing.category=='commercial' %}selected{% endif %}>Коммерция</option></select></label></div>
<div class="grid"><label>Цена <input name="price" value="{{ listing.price or '' }}"></label><label>Instagram URL <input name="instagram_url" value="{{ listing.instagram_url or '' }}"></label></div>
<div class="grid"><label>Название KG <input name="title_ky" value="{{ listing.title_ky or '' }}" required></label><label>Название RU <input name="title_ru" value="{{ listing.title_ru or '' }}" required></label></div>
<div class="grid"><label>Локация KG <input name="location_ky" value="{{ listing.location_ky or '' }}"></label><label>Локация RU <input name="location_ru" value="{{ listing.location_ru or '' }}"></label></div>
<div class="grid"><label>Meta KG <input name="meta_ky" value="{{ ', '.join(load_json_list(listing.meta_ky_json)) if listing.meta_ky_json else '' }}"></label><label>Meta RU <input name="meta_ru" value="{{ ', '.join(load_json_list(listing.meta_ru_json)) if listing.meta_ru_json else '' }}"></label></div>
<div class="grid"><label>Описание KG <textarea name="description_ky">{{ listing.description_ky or '' }}</textarea></label><label>Описание RU <textarea name="description_ru">{{ listing.description_ru or '' }}</textarea></label></div>
<div class="grid"><label>WhatsApp KG <input name="whatsapp_ky" value="{{ listing.whatsapp_ky or '' }}"></label><label>WhatsApp RU <input name="whatsapp_ru" value="{{ listing.whatsapp_ru or '' }}"></label></div>
<div class="grid"><label>Badges KG <input name="badges_ky" value="{{ ', '.join(load_json_list(listing.badges_ky_json)) if listing.badges_ky_json else '' }}"></label><label>Badges RU <input name="badges_ru" value="{{ ', '.join(load_json_list(listing.badges_ru_json)) if listing.badges_ru_json else '' }}"></label></div>
<label>Tags/filters <input name="tags" value="{{ ', '.join(load_json_list(listing.tags_json)) if listing.tags_json else '' }}"></label>
<label>Cover-фото <input type="file" name="cover_image" accept="image/jpeg,image/png,image/webp"></label>
{% if listing.cover_image %}<p class="muted">Текущее фото: {{ listing.cover_image }}</p>{% endif %}
<p><button class="green" type="submit">Сохранить</button></p>
</form>
{% if listing.cover_image %}<form method="post" action="{{ url_for('admin_delete_cover', listing_id=listing.id) }}"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><button class="red" type="submit">Удалить cover-фото</button></form>{% endif %}</main>
"""

if __name__ == "__main__" and len(sys.argv) >= 3 and sys.argv[1] == "hash-password":
    print(generate_password_hash(sys.argv[2]))
    raise SystemExit(0)


app = create_app()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "import-catalog":
        print(json.dumps(import_catalog(app, ROOT / "catalog.json"), ensure_ascii=False))
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
