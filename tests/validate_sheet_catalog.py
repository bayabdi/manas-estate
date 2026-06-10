import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
ADMIN = ROOT / "admin.html"
CATALOG = ROOT / "catalog.json"
README = ROOT / "README.md"
APP = ROOT / "app" / "main.py"
RENDER = ROOT / "render.yaml"
REQUIREMENTS = ROOT / "requirements.txt"
ENV_EXAMPLE = ROOT / ".env.example"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = INDEX.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    app = APP.read_text(encoding="utf-8")
    render = RENDER.read_text(encoding="utf-8")
    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    env_example = ENV_EXAMPLE.read_text(encoding="utf-8")
    listings = catalog.get("listings")

    require(not ADMIN.exists(), "legacy browser-only admin.html must stay removed")
    require("api.github.com/repos" not in html + app, "admin must not depend on GitHub Contents API")
    require("github_pat" not in (html + app).lower(), "admin must not ask for a GitHub PAT")

    require(isinstance(listings, list) and len(listings) >= 6, "catalog.json must seed at least 6 import listings")
    for listing in listings:
        require(listing.get("id"), "each fallback/import listing must have an id")
        require(listing.get("deal") in {"sale", "rent", "buyout"}, "deal must be supported")
        require(listing.get("category") in {"apartment", "house", "land", "commercial"}, "category must be supported")
        require("ky" in listing and "ru" in listing, "each listing must have Kyrgyz and Russian text blocks")

    require("class Listing" in app and "ImportRun" in app, "backend must define listing and import persistence")
    require("from fastapi" in app and "FastAPI(" in app, "backend must be implemented with FastAPI")
    require("/api/listings" in app and "/health" in app, "backend must expose public listings and health endpoints")
    require("ADMIN_PASSWORD_HASH" in app and "SECRET_KEY" in app, "backend must use env-backed admin/session secrets")
    require("validate_runtime_config" in app and "ALLOW_INSECURE_DEV_AUTH" in app, "backend must fail closed unless dev auth is explicitly enabled")
    require("csrf_token" in app and "validate_csrf" in app and 'name="_csrf_token"' in app, "admin POST forms must include CSRF protection")
    require("UPLOAD_DIR" in app and "ALLOWED_IMAGE_EXTENSIONS" in app, "backend must centralize cover photo storage")
    require("detect_image_extension" in app and "Unsupported image content" in app, "cover uploads must validate image content, not only extension")
    require("def import_catalog" in app and "db.get(Listing, listing_id)" in app, "backend must include idempotent catalog import function")
    require("/delete" in app and "admin_listing_delete" in app, "admin CRUD must include protected listing delete")
    require("confirm_import" in app and "уже выполнялся" in app, "admin UI must guard repeated catalog imports")

    require("type: web" in render and "runtime: python" in render, "render.yaml must define a Python web service")
    require("APP_ENV" in render and "production" in render, "Render must run with production config checks")
    require("uvicorn app.main:app --host 0.0.0.0 --port $PORT" in render, "Render start command must run FastAPI on PORT")
    require("fromDatabase" in render and "manas-estate-db" in render, "render.yaml must wire Render Postgres")
    require("disk:" in render and "mountPath: /opt/render/project/src/uploads" in render, "render.yaml must define persistent upload disk")
    require("sync: false" in render and "ADMIN_PASSWORD_HASH" in render, "Render secrets must be dashboard-provided")

    require("fastapi" in requirements.lower() and "uvicorn" in requirements.lower() and "python-multipart" in requirements.lower(), "requirements must include FastAPI/form dependencies")
    require("Flask" not in requirements and "SQLAlchemy" in requirements and "psycopg" in requirements, "requirements must remove Flask and keep DB dependencies")
    require("DATABASE_URL" in env_example and "UPLOAD_DIR" in env_example and "ALLOW_INSECURE_DEV_AUTH=1" in env_example, ".env.example must document explicit local dev auth")
    require("Render" in readme and "UPLOAD_DIR" in readme, "README must document Render and upload persistence")

    print("PASS: backend/admin/Render catalog schema is valid")


if __name__ == "__main__":
    main()
