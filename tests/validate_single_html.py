from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGLE = ROOT / "manas-estate-single.html"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    require(SINGLE.exists(), "manas-estate-single.html must exist")
    html = SINGLE.read_text(encoding="utf-8")

    require("<!doctype html>" in html.lower(), "single file must be a complete HTML document")
    require("data:image/jpeg;base64," in html, "single file must embed images as base64 data URIs")
    require(html.count("data:image/jpeg;base64,") >= 7, "hero + 6 listing images must be embedded")
    require("assets/" not in html, "single file must not reference the assets directory")
    require("data-lang-switch=\"ru\"" in html and "data-lang-switch=\"ky\"" in html, "language switch must remain")
    require('<html lang="ky">' in html, "single file must default the document language to Kyrgyz")
    require('setLanguage(localStorage.getItem("site-lang") || "ky")' in html, "single file must default new visitors to Kyrgyz")
    require("Сатып алуу. Сатуу. Ижара." in html, "single file default hero headline must be Kyrgyz")
    require("function updateWhatsAppLinks" in html and "data-wa-ru=" in html and "data-wa-ky=" in html, "single file must keep language-aware WhatsApp messages")
    require("data-listing-card" in html, "catalog cards must remain")
    broken_questions = chr(63) * 3 + " "
    require(broken_questions not in html and "\ufffd" not in html, "single file must not contain broken encoding markers")

    print("PASS: manas-estate-single.html is self-contained")


if __name__ == "__main__":
    main()
