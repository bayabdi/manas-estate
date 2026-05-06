# Манас Недвижимость — MVP сайт для GitHub Pages

Статический лендинг агентства недвижимости в Жалал-Абаде, собранный по публичным данным Instagram-профиля:
<https://www.instagram.com/jalal_abad__nedvijimost/>

## Что внутри

- `index.html` — весь сайт в одном файле: HTML, CSS, небольшая JS-вставка года.
- `assets/manas-entrance.jpg` — hero-фото для тёмного cinematic дизайна.
- `assets/listing-*.jpg` — временные stock-фото для карточек миникаталога.
- Миникаталог сейчас заполнен демо-объектами. Когда агентство пришлёт реальные данные,
  карточки можно заменить; следующим этапом можно сделать админку для управления объектами.
- Мультиязычность RU/KG работает на клиенте: кнопки `RU` / `KG` переключают ключевые тексты
  и сохраняют выбор в `localStorage`.
- `.nojekyll` — отключает Jekyll на GitHub Pages.
- `robots.txt` — базовые правила индексации.

## Дизайн и изображения

Текущий визуальный стиль — SpaceX-inspired: тёмный full-screen hero, крупная типографика,
минимум текста и сильные CTA. Это вдохновение по визуальному языку, без копирования кода или бренда SpaceX.

Hero-фото и фото карточек: Unsplash / Unsplash License. Hero: Isakov Eldiiar,
Kyrgyzstan landscape. Фото карточек используются как временные stock-заглушки.
После получения реальных фото Манаса, объектов или офиса агентства их лучше заменить.

## Публикация через GitHub Pages

1. Создайте репозиторий на GitHub, например `jalal-abad-nedvijimost`.
2. Загрузите в него файлы из этой папки: `index.html`, `.nojekyll`, `robots.txt`, `README.md`.
3. Откройте **Settings → Pages**.
4. В **Build and deployment** выберите:
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/ (root)`
5. Сохраните настройки. Через 1–3 минуты сайт будет доступен по адресу:
   `https://<github-user>.github.io/jalal-abad-nedvijimost/`

## Публикация через git

```bash
git init
git add index.html .nojekyll robots.txt README.md
git commit -m "Launch real estate MVP landing

Constraint: GitHub Pages static hosting from repository root
Confidence: high
Scope-risk: narrow
Tested: local static HTML validation
Not-tested: production GitHub Pages deployment without remote credentials"
git branch -M main
git remote add origin https://github.com/<github-user>/jalal-abad-nedvijimost.git
git push -u origin main
```

После push включите GitHub Pages в настройках репозитория.
