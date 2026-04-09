# Техчиталка PDF (PDF → перевод → озвучка + текст)

Веб-приложение: загрузка PDF, извлечение текста (при необходимости OCR через OpenAI Vision), определение языка, перевод EN→RU, озвучка OpenAI TTS. В читалке текст текущего **сегмента** показывается вместе с аудио этого сегмента (синхронизация по абзацам/сегментам, не пословно).

**Стек:** Python 3.11, FastAPI, Celery, Redis, PostgreSQL, React (Vite) + TanStack Query.

## Быстрый старт (Docker)

1. Скопируйте `backend/env.example` в `backend/.env` и задайте `OPENAI_API_KEY` и при необходимости `JWT_SECRET`.

2. Из корня проекта:

```powershell
docker compose up --build
```

- API: http://localhost:8000  
- Документация: http://localhost:8000/docs  
- Фронтенд: соберите `frontend` (`npm run build`) и раздайте статику через nginx или запустите dev-сервер отдельно (см. ниже).

## Локальная разработка (PowerShell)

**База:** в `env.example` по умолчанию **SQLite** (`./data/app.db`) — отдельно PostgreSQL не нужен. Для полного стека как в Docker задайте в `.env` URL PostgreSQL и поднимите `docker compose up db redis`.

**Ошибка `Connect call failed ... 5432`:** в `.env` всё ещё указан PostgreSQL, а сервер не запущен. Либо переключитесь на строки SQLite из `env.example`, либо выполните `docker compose up db -d` и проверьте `DATABASE_URL`.

**Backend:** запускать **только из каталога `backend`**, иначе `ModuleNotFoundError: No module named 'app'` и фронт покажет **Failed to fetch**.

```powershell
cd backend
Copy-Item env.example .env
# отредактируйте .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Или: `.\run_api.ps1` из каталога `backend` (после активации venv). **Не запускайте uvicorn из `frontend`**.

**Redis (брокер для Celery):** без него задача обработки PDF не выполнится. Поднимите из **корня репозитория**:

```powershell
docker compose up redis -d
```

Затем в **отдельном окне** воркер Celery (`--pool=solo` на Windows). В **другом окне** — API.

В `backend/.env` можно оставить **`CELERY_RESULT_BACKEND` пустым** — результаты задач в Redis не хранятся, но очередь всё равно требует брокер (`CELERY_BROKER_URL`).

**Ошибка `Cannot connect to redis://localhost:6379`** — Redis не запущен. После загрузки PDF без Redis API вернёт **503** с подсказкой запустить Redis.

**Worker (отдельное окно)** — сначала **`cd backend`**, иначе `ModuleNotFoundError: No module named 'app'`.

На **Windows** у Celery пул по умолчанию (`prefork`) даёт `PermissionError` на семафорах — используйте **`--pool=solo`** (или `threads`):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
```

Или: `.\run_celery.ps1` (уже с `--pool=solo`).

**Запуск из корня репозитория** (без `cd backend`):

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\backend\.venv\Scripts\Activate.ps1
celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
```

**Frontend:**

```powershell
cd frontend
npm install
npm run dev
```

В режиме `npm run dev` запросы к API идут на **`/api/v1`** и **проксируются Vite** на `http://127.0.0.1:8000` (см. `frontend/vite.config.ts`). Убедитесь, что **uvicorn запущен на порту 8000**.

**«Failed to fetch» на регистрации:**

1. API должен быть запущен из **`backend`**, порт **8000** (проверка: откройте http://127.0.0.1:8000/docs ).
2. В **`frontend/.env.local`** не задавайте `VITE_API_BASE`, если используете прокси Vite (тогда запросы идут на `/api/v1` с того же origin, что и `npm run dev`).
3. Откройте приложение с **`http://localhost:5173`** или **`http://127.0.0.1:5173`**. При своём `CORS_ORIGINS` в `backend/.env` перечислите оба origin через запятую.

Прямой URL к API (без прокси): `VITE_API_BASE=http://127.0.0.1:8000/api/v1` в `.env.local` — только если бэкенд точно доступен по этому адресу.

## Тесты

```powershell
cd backend
pytest
```

## Структура

- `backend/app` — FastAPI, модели, конвейер, Celery-задачи  
- `frontend` — React SPA  
- `docker-compose.yml` — PostgreSQL, Redis, API, worker  

Файлы книг и аудио хранятся в `STORAGE_PATH` (в Docker: том `storage_data`).
