# apexjld — Admin + Backend + Render каталог

Статический MVP мигрирует в небольшой FastAPI backend/admin для агентства недвижимости Манаса / Жалал-Абада.

Основной язык публичного сайта — кыргызский. Русский доступен через переключатель `RU / KG`.

## Что внутри

- `index.html` — публичный сайт-визитка и клиентский каталог, теперь читающий `/api/listings`.
- `app/main.py` — FastAPI backend: public API, admin login, CRUD объектов, импорт `catalog.json`, загрузка одного cover-фото.
- `catalog.json` — seed/import-файл для одноразовой миграции старых объектов в backend DB.
- `render.yaml` — Render Blueprint: Web Service + Render Postgres + persistent disk для `UPLOAD_DIR`.
- `.env.example` — локальные переменные окружения без секретов.
- `tests/` — статические проверки и backend smoke/unit tests.

Legacy `admin.html` не используется: админка живёт в backend по `/admin`.

## Локальный запуск

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main import-catalog
python -m app.main
```

Откройте:

- сайт: <http://localhost:8000/>
- админка: <http://localhost:8000/admin>
- health: <http://localhost:8000/health>

Dev fallback включается только явно через `ALLOW_INSECURE_DEV_AUTH=1` в локальном `.env`: логин `admin`, пароль `admin`.
Без этого backend требует `ADMIN_PASSWORD_HASH`. Для production задайте hash:

```bash
python -m app.main hash-password 'strong-password'
```

и положите результат в `ADMIN_PASSWORD_HASH` в Render Environment. В production приложение откажется стартовать,
если нет сильного `SECRET_KEY`, `ADMIN_PASSWORD_HASH` или Render Postgres `DATABASE_URL`.

## Модель каталога

Нормальный source of truth после cutover — backend database. Google Sheet больше не является рабочим источником данных.

Объект поддерживает:

- `published` / скрыть-показать;
- `sort`;
- `deal`: `sale`, `rent`, `buyout`;
- `category`: `apartment`, `house`, `land`, `commercial`;
- `price`;
- RU/KG title, location, meta, description;
- WhatsApp текст RU/KG;
- Instagram URL;
- tags/filters;
- одно `coverImageUrl`.

`catalog.json` сохраняется как seed/import источник. Импорт idempotent по стабильному `id`: повторный запуск обновляет существующие записи и не создаёт дубли.
Seed-объекты импортируются без cover-фото: менеджер добавляет фото через админку после импорта или делает отдельный backfill.

## Cover-фото и UPLOAD_DIR

MVP поддерживает одно cover-фото на объект.

- допустимые расширения: `jpg`, `jpeg`, `png`, `webp`;
- лимит по умолчанию: 8 MB (`MAX_IMAGE_BYTES`);
- файлы пишутся только в `UPLOAD_DIR`;
- локально по умолчанию: `uploads/`;
- на Render: `/opt/render/project/src/uploads`.

Важно: Render filesystem по умолчанию ephemeral, поэтому production-фото должны лежать на persistent disk, смонтированном в `UPLOAD_DIR`.

## Render deploy

`render.yaml` описывает:

- Web Service `manas-estate`;
- Render Postgres `manas-estate-db`;
- persistent disk `uploads`;
- `healthCheckPath: /health`;
- start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

Переменные/secrets в Render:

```text
DATABASE_URL            # from Render Postgres
APP_ENV=production
SECRET_KEY              # generateValue в Blueprint
ADMIN_USERNAME          # задать в Dashboard
ADMIN_PASSWORD_HASH     # задать в Dashboard
UPLOAD_DIR=/opt/render/project/src/uploads
```

Реальный deploy credential-gated: нужен доступ к Render/GitHub. После deploy выполните smoke:

1. `/health` возвращает `ok: true`.
2. `/admin` доступен только после логина.
3. Импортируйте `catalog.json` или создайте объект вручную.
4. Опубликуйте объект с cover-фото.
5. Проверьте, что `/` показывает объект из backend API.
6. Redeploy/restart: DB запись и cover-фото должны сохраниться.

Persistent disk означает single-instance сервис и отсутствие zero-downtime deploy для этого сервиса. Для будущих галерей/масштабирования стоит перейти на external object storage.

## Проверка

Статические проверки:

```bash
python3 tests/validate_site.py
python3 tests/validate_sheet_catalog.py
python3 tests/validate_frontend_runtime.py
```

Backend tests после установки зависимостей:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Все проверки должны завершаться `PASS` / `OK`.
