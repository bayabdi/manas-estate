# Manas Estate — сайт и админка для GitHub Pages

Статический сайт агентства недвижимости для Манаса / Жалал-Абада:
<https://bayabdi.github.io/manas-estate/>

Основной язык сайта — кыргызский. Русский доступен через переключатель `RU / KG`.

## Что внутри

- `index.html` — основной сайт-визитка + миникаталог.
- `catalog.json` — данные объектов, которые читает сайт.
- `admin.html` — простая админка для изменения каталога без программирования.
- `assets/listing-*.jpg` — стартовые фото объектов.
- `assets/listings/` — папка для фото, загруженных через админку.
- `manas-estate-single.html` — один самодостаточный HTML-файл для отправки/демо.
- `.nojekyll` — отключает Jekyll на GitHub Pages.
- `robots.txt` — базовые правила индексации.

## Как пользоваться админкой

Админка доступна по адресу:
<https://bayabdi.github.io/manas-estate/admin.html>

1. Введите GitHub PAT.
2. Нажмите **Загрузить каталог**.
3. Добавьте или отредактируйте объект.
4. Загрузите фото объекта.
5. Нажмите **Сохранить объект**.
6. Нажмите **Сохранить на сайт**.

Админка сохраняет изменения в:

- `catalog.json`
- `assets/listings/*.jpg`

Токен в файлы проекта не записывается.

## Права PAT для админки

Лучше использовать отдельный fine-grained token только для репозитория:
`bayabdi/manas-estate`

Минимальные права:

- `Contents: Read and write`
- `Metadata: Read-only`

После работы токен можно удалить/revoke в GitHub settings.

## Фото и нагрузка

Админка уменьшает фото в браузере до 1600px и сохраняет JPEG с качеством `0.82`.
Это снижает вес страницы и расход GitHub Pages bandwidth.

GitHub Pages имеет soft limit примерно 100 GB bandwidth/month, поэтому для MVP агентства
этого достаточно. Если объектов и трафика станет много, фото лучше вынести в Cloudinary,
ImageKit или Cloudflare R2.

## Публикация

GitHub Pages включён из ветки:

- Branch: `main`
- Folder: `/ (root)`

Адрес сайта:
<https://bayabdi.github.io/manas-estate/>

## Проверка

```bash
python tests/validate_site.py
python tests/validate_admin.py
python tests/validate_single_html.py
```
