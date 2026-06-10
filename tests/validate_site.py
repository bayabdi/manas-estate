from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
README = ROOT / "README.md"
CATALOG = ROOT / "catalog.json"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if "id" in attrs_dict:
            self.ids.add(attrs_dict["id"])
        if tag == "a" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"])
        if tag == "img":
            self.images.append(attrs_dict)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = INDEX.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    parser = SiteParser()
    parser.feed(html)
    default_html = html.split("const translations", 1)[0]

    for section in ["quick-search", "catalog", "trust", "process", "contacts"]:
        require(section in parser.ids, f"index.html must contain #{section} section")

    require('const LISTINGS_API_URL = "/api/listings"' in html, "site must load catalog from backend API")
    require('const SITE_SETTINGS_API_URL = "/api/site-settings"' in html, "site must load editable site settings from backend API")
    require("loadSiteSettings" in html and "applySiteSettings" in html, "front-end must apply admin-managed site settings")
    require("https://bayabdi.github.io/manas-estate/" not in html, "site SEO URLs must no longer point to GitHub Pages")
    require("https://manas-estate.onrender.com/" in html, "site must declare the Render public URL")
    require("GOOGLE_SHEET_CSV_URL" not in html, "public site must not use Google Sheet CSV as normal source")
    require("loadFallbackCatalog" not in html, "public site must not silently fall back to legacy catalog.json")
    require("каталог временно недоступен" in html and "каталог убактылуу жеткиликсиз" in html, "site must show buyer-facing catalog unavailable copy")
    require("coverImageUrl" in html and "cover-image" in html, "cards must support one cover photo")
    require("data-filter-button" in html and html.count("data-filter-button") >= 8, "catalog must keep filters")
    require("data-listing-card" in html, "rendered cards must expose data-listing-card metadata")
    require("safeInstagramUrl" in html, "front-end must sanitize public Instagram URLs")
    require("function dealLabel" in html and "function categoryLabel" in html and "function textFor" in html, "runtime catalog helpers must be defined")

    require(any(link.startswith("https://wa.me/996888001002") for link in parser.links), "site must include WhatsApp CTA")
    require(any("instagram.com/jalal_abad__nedvijimost" in link for link in parser.links), "site must link to Instagram profile")
    require(not any(link == "/admin" for link in parser.links), "public buyer-facing site must not show admin links")

    require('<meta name="viewport"' in html, "site must include responsive viewport meta")
    require('property="og:title"' in html and 'name="twitter:card"' in html, "site must include social SEO tags")
    require('"@type":"RealEstateAgent"' in html or '"@type": "RealEstateAgent"' in html, "site must include RealEstateAgent schema")
    require('<html lang="ky">' in html, "site must default document language to Kyrgyz")
    require('setLanguage(localStorage.getItem("site-lang") || "ky")' in html, "new visitors must default to Kyrgyz")
    require("Ишенимдүү мүлк тандоо" in default_html, "default hero headline must be a stronger Kyrgyz value proposition")
    require("Купить. Продать. Арендовать." not in default_html, "Russian hero headline must not be default visible copy")
    for phrase in [
        "убактыңызды үнөмдөйбүз",
        "Эмнеден баштайбыз?",
        "Эмне үчүн бизге жазышат",
        "Бир билдирүү — тандоо башталат",
        "Көрүүгө чейин 4 кадам",
    ]:
        require(phrase in html, f"site must include strengthened buyer-facing phrase: {phrase}")
    for internal_word in ["Admin", "админка", "админке", "админкадан", "Backend", "backend", "Render backend", "GitHub", "cover-фото"]:
        require(internal_word not in default_html, f"public visible copy must not expose internal term: {internal_word}")

    require("backend" in readme.lower() and "render" in readme.lower(), "README must explain backend/Render workflow")
    require("python3 tests/validate_site.py" in readme, "README must document static validation")
    require(CATALOG.exists(), "catalog.json import seed must exist")

    print("PASS: backend-powered public site shell is wired")


if __name__ == "__main__":
    main()
