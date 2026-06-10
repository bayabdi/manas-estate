import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ALLOW_INSECURE_DEV_AUTH", "1")
os.environ.setdefault("SECRET_KEY", "test-module-secret-that-is-long-enough")

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import ImportRun, Listing, SiteSettings, check_password_hash, create_app, generate_password_hash, import_catalog


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
BAD_IMAGE_BYTES = b"not really an image"


def csrf_from_html(html: str) -> str:
    match = re.search(r'name="_csrf_token" value="([^"]+)"', html)
    if not match:
        raise AssertionError("CSRF token not found in form")
    return match.group(1)


class BackendAppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.upload_dir = root / "uploads"
        self.app = create_app({
            "TESTING": True,
            "DATABASE_URL": f"sqlite:///{root / 'test.db'}",
            "UPLOAD_DIR": str(self.upload_dir),
            "SECRET_KEY": "test-secret-that-is-long-enough-for-session",
            "ALLOW_INSECURE_DEV_AUTH": True,
        })
        self.client = TestClient(self.app, follow_redirects=False)

    def tearDown(self):
        self.app.db_session.remove()
        self.app.engine.dispose()
        self.tmp.cleanup()

    def csrf_token(self, path: str = "/admin/login") -> str:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return csrf_from_html(response.text)

    def login(self):
        token = self.csrf_token("/admin/login")
        return self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin", "_csrf_token": token},
            follow_redirects=True,
        )

    def dashboard_csrf(self) -> str:
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        return csrf_from_html(response.text)

    def create_listing(self, listing_id="test-listing", cover_bytes=PNG_BYTES, filename="cover.png", follow_redirects=True):
        self.login()
        token = self.csrf_token("/admin/listings/new")
        data = {
            "_csrf_token": token,
            "published": "on",
            "id": listing_id,
            "sort": "1",
            "deal": "sale",
            "category": "apartment",
            "price": "$1",
            "instagram_url": "https://www.instagram.com/p/example/",
            "title_ky": "Тест батир",
            "title_ru": "Тест квартира",
            "location_ky": "Манас",
            "location_ru": "Манас",
            "meta_ky": "50 м², 2 бөлмө",
            "meta_ru": "50 м², 2 комнаты",
            "description_ky": "Тест",
            "description_ru": "Тест",
            "whatsapp_ky": "Саламатсызбы",
            "whatsapp_ru": "Здравствуйте",
            "badges_ky": "Сатуу, Батир",
            "badges_ru": "Продажа, Квартира",
            "tags": "sale, apartment",
        }
        files = {"cover_image": (filename, io.BytesIO(cover_bytes), "image/png")}
        return self.client.post("/admin/listings/new", data=data, files=files, follow_redirects=follow_redirects)

    def test_catalog_import_is_idempotent(self):
        first = import_catalog(self.app, Path("catalog.json"))
        second = import_catalog(self.app, Path("catalog.json"))
        rows = self.app.db_session.scalars(select(Listing)).all()
        self.assertGreaterEqual(first["created"], 6)
        self.assertEqual(second["created"], 0)
        self.assertGreaterEqual(second["updated"], 6)
        self.assertEqual(len(rows), len(json.loads(Path("catalog.json").read_text(encoding="utf-8"))["listings"]))

    def test_public_api_returns_only_published(self):
        import_catalog(self.app, Path("catalog.json"))
        hidden = self.app.db_session.scalars(select(Listing).limit(1)).first()
        hidden.published = False
        hidden_id = hidden.id
        self.app.db_session.commit()
        response = self.client.get("/api/listings")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()["listings"]}
        self.assertNotIn(hidden_id, ids)

    def test_admin_requires_login_and_logout_invalidates_session(self):
        self.assertEqual(self.client.get("/admin").status_code, 302)
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Каталог".encode(), response.content)
        self.assertIn("Настройки сайта".encode(), response.content)
        self.assertNotIn("Повторный импорт".encode(), response.content)
        self.assertNotIn("Импорт catalog.json".encode(), response.content)
        token = self.dashboard_csrf()
        self.client.post("/admin/logout", data={"_csrf_token": token})
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_site_settings_api_and_admin_update(self):
        defaults = self.client.get("/api/site-settings")
        self.assertEqual(defaults.status_code, 200)
        self.assertEqual(defaults.json()["contacts"]["whatsappPhone"], "996888001002")
        self.assertIn("Ишенимдүү мүлк тандоо", defaults.json()["copy"]["ky"]["heroTitle"])

        self.login()
        token = self.csrf_token("/admin/settings")
        response = self.client.post(
            "/admin/settings",
            data={
                "_csrf_token": token,
                "phone_primary": "0777 111 222",
                "phone_secondary": "0777 333 444",
                "whatsapp_phone": "996777111222",
                "instagram_url": "https://www.instagram.com/example_realty/",
                "hero_kicker_ky": "Манас · жеке тандоо",
                "hero_kicker_ru": "Манас · личный подбор",
                "hero_title_ky": "Үйдү ишеним менен тандаңыз",
                "hero_title_ru": "Подберите дом спокойно",
                "hero_lead_ky": "Биз район, баа жана шарттарды тактап беребиз.",
                "hero_lead_ru": "Уточним район, цену и условия заранее.",
                "cta_text_ky": "Мага вариант керек",
                "cta_text_ru": "Хочу варианты",
                "seo_title_ky": "Манас кыймылсыз мүлк",
                "seo_title_ru": "Недвижимость Манас",
                "seo_description_ky": "Манаста кыймылсыз мүлк тандоо.",
                "seo_description_ru": "Подбор недвижимости в Манасе.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Настройки сохранены".encode(), response.content)

        payload = self.client.get("/api/site-settings").json()
        self.assertEqual(payload["contacts"]["whatsappPhone"], "996777111222")
        self.assertEqual(payload["contacts"]["phones"], ["0777 111 222", "0777 333 444"])
        self.assertEqual(payload["contacts"]["instagramUrl"], "https://www.instagram.com/example_realty/")
        self.assertEqual(payload["copy"]["ky"]["heroTitle"], "Үйдү ишеним менен тандаңыз")
        self.assertEqual(payload["copy"]["ru"]["ctaText"], "Хочу варианты")

        row = self.app.db_session.get(SiteSettings, 1)
        self.assertEqual(row.whatsapp_phone, "996777111222")

    def test_admin_rejects_missing_csrf(self):
        login_response = self.client.post("/admin/login", data={"username": "admin", "password": "admin"})
        self.assertEqual(login_response.status_code, 400)
        self.login()
        create_response = self.client.post("/admin/listings/new", data={"id": "no-csrf"})
        self.assertEqual(create_response.status_code, 400)

    def test_admin_can_create_listing_with_cover_photo(self):
        response = self.create_listing()
        self.assertEqual(response.status_code, 200)
        self.app.db_session.remove()
        listing = self.app.db_session.get(Listing, "test-listing")
        self.assertIsNotNone(listing)
        self.assertTrue((self.upload_dir / listing.cover_image).exists())
        api = self.client.get("/api/listings").json()
        created = next(item for item in api["listings"] if item["id"] == "test-listing")
        self.assertTrue(created["coverImageUrl"].startswith("/uploads/"))

    def test_admin_rejects_fake_image_content(self):
        response = self.create_listing("fake-image", BAD_IMAGE_BYTES, "cover.png", follow_redirects=False)
        self.assertEqual(response.status_code, 400)
        self.app.db_session.remove()
        self.assertIsNone(self.app.db_session.get(Listing, "fake-image"))

    def test_admin_can_delete_listing_and_cover_photo(self):
        self.create_listing("delete-me")
        listing = self.app.db_session.get(Listing, "delete-me")
        cover_path = self.upload_dir / listing.cover_image
        self.assertTrue(cover_path.exists())
        token = self.dashboard_csrf()
        response = self.client.post("/admin/listings/delete-me/delete", data={"_csrf_token": token}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.app.db_session.remove()
        self.assertIsNone(self.app.db_session.get(Listing, "delete-me"))
        self.assertFalse(cover_path.exists())

    def test_admin_repeated_import_requires_confirmation(self):
        self.login()
        token = self.dashboard_csrf()
        first = self.client.post("/admin/import", data={"_csrf_token": token}, follow_redirects=True)
        self.assertEqual(first.status_code, 200)
        token = self.dashboard_csrf()
        second = self.client.post("/admin/import", data={"_csrf_token": token}, follow_redirects=True)
        self.assertEqual(second.status_code, 200)
        self.assertIn("уже выполнялся".encode(), second.content)
        self.assertEqual(len(self.app.db_session.scalars(select(ImportRun)).all()), 1)
        token = self.dashboard_csrf()
        confirmed = self.client.post("/admin/import", data={"_csrf_token": token, "confirm_import": "IMPORT"}, follow_redirects=True)
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(len(self.app.db_session.scalars(select(ImportRun)).all()), 2)

    def test_production_startup_requires_secret_hash_and_postgres(self):
        root = Path(self.tmp.name)
        with self.assertRaisesRegex(RuntimeError, "Postgres"):
            create_app({
                "TESTING": False,
                "APP_ENV": "production",
                "DATABASE_URL": f"sqlite:///{root / 'bad.db'}",
                "UPLOAD_DIR": str(self.upload_dir),
                "SECRET_KEY": "short",
                "ADMIN_PASSWORD_HASH": "",
            })
        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
            create_app({
                "TESTING": False,
                "APP_ENV": "production",
                "DATABASE_URL": "postgresql://user:pass@localhost/db",
                "UPLOAD_DIR": str(self.upload_dir),
                "SECRET_KEY": "short",
                "ADMIN_PASSWORD_HASH": "hash",
            })
        with self.assertRaisesRegex(RuntimeError, "ADMIN_PASSWORD_HASH"):
            create_app({
                "TESTING": False,
                "APP_ENV": "production",
                "DATABASE_URL": "postgresql://user:pass@localhost/db",
                "UPLOAD_DIR": str(self.upload_dir),
                "SECRET_KEY": "x" * 32,
                "ADMIN_PASSWORD_HASH": "",
            })


    def test_password_hash_command_output_is_verifiable(self):
        password_hash = generate_password_hash("strong-password")
        self.assertTrue(check_password_hash(password_hash, "strong-password"))
        self.assertFalse(check_password_hash(password_hash, "wrong-password"))

    def test_restart_persistence_with_same_upload_dir(self):
        self.create_listing("persistent-listing")
        self.app.engine.dispose()
        restarted = create_app({
            "TESTING": True,
            "DATABASE_URL": self.app.config["DATABASE_URL"],
            "UPLOAD_DIR": str(self.upload_dir),
            "SECRET_KEY": "test-secret-that-is-long-enough-for-session",
            "ALLOW_INSECURE_DEV_AUTH": True,
        })
        payload = TestClient(restarted).get("/api/listings").json()
        item = next(row for row in payload["listings"] if row["id"] == "persistent-listing")
        self.assertTrue(item["coverImageUrl"].startswith("/uploads/"))
        self.assertTrue((self.upload_dir / item["coverImageUrl"].rsplit("/", 1)[-1]).exists())

    def test_health_does_not_leak_secrets(self):
        response = self.client.get("/health")
        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("test-secret", body)
        self.assertNotIn("DATABASE_URL", body)
        self.assertNotIn("ADMIN", body)


if __name__ == "__main__":
    unittest.main()
