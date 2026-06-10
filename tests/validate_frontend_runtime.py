import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def main():
    html = INDEX.read_text(encoding="utf-8")
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    script = script.split('document.getElementById("year").textContent', 1)[0]
    node_program = f"""
const grid = {{ innerHTML: "" }};
const node = {{ dataset: {{}}, classList: {{ toggle() {{}} }}, setAttribute() {{}}, textContent: "" }};
const document = {{
  documentElement: {{ lang: "ky" }},
  querySelector(selector) {{
    if (selector === "[data-catalog-grid]") return grid;
    if (selector === 'meta[name="description"]') return node;
    return null;
  }},
  querySelectorAll() {{ return []; }},
  getElementById() {{ return node; }}
}};
const localStorage = {{ getItem() {{ return null; }}, setItem() {{}} }};
{script}
if (typeof renderCatalog !== "function" || typeof dealLabel !== "function" || typeof categoryLabel !== "function" || typeof textFor !== "function" || typeof categoryIcon !== "function") {{
  throw new Error("catalog helper functions are not available");
}}
renderCatalog({{ listings: [{{
  id: "runtime-1",
  active: true,
  sort: 1,
  deal: "sale",
  category: "apartment",
  filters: ["sale", "apartment"],
  price: "$100",
  instagramUrl: "https://www.instagram.com/p/example/",
  coverImageUrl: "/uploads/cover.png",
  whatsapp: {{ ky: "Саламатсызбы", ru: "Здравствуйте" }},
  badges: {{ ky: ["Сатуу", "Батир"], ru: ["Продажа", "Квартира"] }},
  ky: {{ title: "Тест батир", location: "Манас", meta: ["50 м²", "2 бөлмө"], description: "Сүрөтү бар объект" }},
  ru: {{ title: "Тест квартира", location: "Манас", meta: ["50 м²", "2 комнаты"], description: "Объект с фото" }}
}}] }});
if (!grid.innerHTML.includes("listing-card")) throw new Error("listing card was not rendered");
if (!grid.innerHTML.includes("cover-image")) throw new Error("cover image was not rendered");
if (!grid.innerHTML.includes("Тест батир")) throw new Error("localized title was not rendered");
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
        handle.write(node_program)
        path = handle.name
    result = subprocess.run(["node", path], text=True, capture_output=True)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    print("PASS: frontend catalog runtime renders a mocked backend listing")


if __name__ == "__main__":
    main()
