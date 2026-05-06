from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
README = ROOT / "README.md"
HERO_IMAGE = ROOT / "assets" / "manas-entrance.jpg"
LISTING_IMAGES = [
    ROOT / "assets" / "listing-apartment-sale.jpg",
    ROOT / "assets" / "listing-apartment-rent.jpg",
    ROOT / "assets" / "listing-house.jpg",
    ROOT / "assets" / "listing-land.jpg",
    ROOT / "assets" / "listing-apartment-urgent.jpg",
    ROOT / "assets" / "listing-commercial.jpg",
]


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.listing_cards = 0
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if "id" in attrs_dict:
            self.ids.add(attrs_dict["id"])
        if "data-listing-card" in attrs_dict:
            self.listing_cards += 1
        if tag == "a" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"])


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = INDEX.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    parser = SiteParser()
    parser.feed(html)
    default_html = html.split("const translations", 1)[0]

    require("catalog" in parser.ids, "index.html must contain #catalog mini-catalog section")
    require("quick-search" in parser.ids, "index.html must contain quick-search intent section")
    require("trust" in parser.ids, "index.html must contain trust proof section")
    require(
        parser.listing_cards >= 6,
        f"expected at least 6 demo listing cards, found {parser.listing_cards}",
    )
    require(
        html.count('data-filter-button') >= 5,
        "catalog must include filter buttons for browsing listing types",
    )
    require("data-filter=\"sale" in html and "data-filter=\"rent" in html, "catalog cards must expose sale/rent filter metadata")
    require(
        any(link.startswith("https://wa.me/996888001002") for link in parser.links),
        "site must include WhatsApp CTA for 0888 001 002",
    )
    require(
        any("instagram.com/jalal_abad__nedvijimost" in link for link in parser.links),
        "site must link to the Instagram profile",
    )
    require("демо-объекты" in html.lower(), "catalog must clearly mark listings as demo objects")
    require("64k" in html.lower(), "site must make Instagram trust signal visible")
    require('<meta name="viewport"' in html, "site must include responsive viewport meta")
    require("mobile-cta" in html and ("@media (max-width: 640px)" in html or "@media (max-width:640px)" in html), "site must include mobile CTA and phone breakpoint")
    require('property="og:title"' in html and 'name="twitter:card"' in html, "site must include Open Graph and Twitter SEO tags")
    require('"@type":"RealEstateAgent"' in html or '"@type": "RealEstateAgent"' in html, "site must include RealEstateAgent schema")
    require('"@type":"ItemList"' in html or '"@type": "ItemList"' in html, "site must include ItemList schema for demo catalog")
    require('<meta name="robots"' in html, "site must include robots SEO meta")
    require("spacex-inspired" in html, "site must mark the SpaceX-inspired visual direction")
    require("cinematic-hero" in html and "100svh" in html, "site must include full-screen cinematic hero")
    require("assets/manas-entrance.jpg" in html, "site must use local Manas/Jalal-Abad hero photo asset")
    require(HERO_IMAGE.exists() and HERO_IMAGE.stat().st_size > 10_000, "hero photo asset must exist locally")
    for image in LISTING_IMAGES:
        require(image.exists() and image.stat().st_size > 10_000, f"listing image asset missing or too small: {image.name}")
        require(f"assets/{image.name}" in html, f"index.html must reference listing image: {image.name}")
        require(f'<img src="assets/{image.name}"' in html, f"listing image must be rendered with img tag: {image.name}")
    require(
        ("Wikimedia Commons" in html or "Unsplash" in html) and ("public domain" in html.lower() or "license" in html.lower()),
        "site must include image attribution and license note",
    )
    require('data-lang-switch="ru"' in html and 'data-lang-switch="ky"' in html, "site must include RU/KG language switch buttons")
    require("const translations" in html and "document.documentElement.lang" in html, "site must include client-side translation dictionary")
    require('data-i18n="hero.title"' in html and '"ky"' in html, "hero copy must be translatable to Kyrgyz")
    require("localStorage" in html and "site-lang" in html, "language choice must persist in localStorage")
    require('<html lang="ky">' in html, "site must default the document language to Kyrgyz")
    require('data-lang-switch="ky">KG</button>' in html, "site must include the Kyrgyz language switch button")
    require('data-lang-switch="ru">RU</button>' in html, "site must keep Russian available as a switchable language")
    require('setLanguage(localStorage.getItem("site-lang") || "ky")' in html, "new visitors must default to Kyrgyz")
    require("Сатып алуу. Сатуу. Ижара." in default_html, "default hero headline must be Kyrgyz")
    require("Купить. Продать. Арендовать." not in default_html, "Russian hero headline must not be the default visible copy")
    require('data-wa-ru=' in html and 'data-wa-ky=' in html, "WhatsApp CTAs must define per-language message text")
    require(html.count('data-wa-intent=') >= 8, "WhatsApp CTAs must expose user intent metadata")
    require("function updateWhatsAppLinks" in html and "encodeURIComponent(message)" in html, "WhatsApp links must update messages from active language")
    require("\u042f \u0445\u043e\u0447\u0443 \u043a\u0443\u043f\u0438\u0442\u044c" in html, "buy intent must have Russian WhatsApp message")
    require("\u0421\u0430\u0442\u044b\u043f \u0430\u043b\u0433\u044b\u043c \u043a\u0435\u043b\u0435\u0442" in html, "buy intent must have Kyrgyz WhatsApp message")
    require("\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!" in html, "Russian WhatsApp messages must start politely with a greeting")
    require("\u0421\u0430\u043b\u0430\u043c\u0430\u0442\u0441\u044b\u0437\u0431\u044b!" in html, "Kyrgyz WhatsApp messages must start politely with a greeting")
    require("админ" in readme.lower(), "README must mention future admin/catalog replacement path")

    print("PASS: static MVP contains mini-catalog, CTAs, and GitHub Pages docs")


if __name__ == "__main__":
    main()
