import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN = ROOT / "admin.html"
CATALOG = ROOT / "catalog.json"
INDEX = ROOT / "index.html"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    require(ADMIN.exists(), "admin.html must exist")
    require(CATALOG.exists(), "catalog.json must exist")

    admin = ADMIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    require("data-admin-app" in admin, "admin.html must expose an admin app shell")
    require('type="password"' in admin and "github_pat" in admin, "admin must accept a GitHub PAT without displaying it")
    require("api.github.com/repos" in admin and "/contents/" in admin, "admin must save files through GitHub Contents API")
    require("catalog.json" in admin, "admin must update catalog.json")
    require("assets/listings/" in admin, "admin must upload listing photos under assets/listings/")
    require("canvas" in admin and "toBlob" in admin, "admin must resize/compress uploaded photos in browser")
    require("localstorage" not in admin.lower(), "admin must not persist the PAT in localStorage")

    require(isinstance(catalog.get("listings"), list), "catalog.json must contain a listings array")
    require(len(catalog["listings"]) >= 6, "catalog.json must seed at least 6 listings")
    for listing in catalog["listings"]:
        require(listing.get("id"), "each listing must have an id")
        require(listing.get("image", "").startswith("assets/"), "each listing must have a local image path")
        require("instagramUrl" in listing, "each listing must support an Instagram link")
        require("ky" in listing and "ru" in listing, "each listing must have Kyrgyz and Russian text blocks")
        require(listing["ky"].get("title") and listing["ru"].get("title"), "listing title must be bilingual")

    require("catalog.json" in index and "renderCatalog" in index, "site must load and render catalog.json")
    require("instagramUrl" in index, "site catalog cards must render Instagram links when present")
    require("fallbackCatalog" in index, "site must keep a fallback catalog when JSON fetch fails")

    print("PASS: admin MVP and JSON catalog are wired")


if __name__ == "__main__":
    main()
