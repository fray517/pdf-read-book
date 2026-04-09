# Простой backend (по plan.md, этап 1.1)

## Один раз: виртуальное окружение и зависимости

```powershell
cd C:\Users\feden\pdf-book-reader\simple
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Если pip пишет `Read timed out` к pypi.org

Увеличьте таймаут и при необходимости повторите:

```powershell
pip install --default-timeout=120 --retries 10 -r requirements.txt
```

Либо попробуйте другую сеть (например раздача с телефона) или VPN. Зеркала PyPI иногда публикуют региональные провайдеры — URL уточняйте у них.

### `ModuleNotFoundError: No module named 'pydantic_settings'`

После этапа 1.2 в `requirements.txt` добавлены новые пакеты. Активируйте то же окружение, что и для uvicorn, и выполните:

```powershell
pip install -r requirements.txt
```

(Папка venv может называться `.venv` или `venv` — неважно, главное — один и тот же интерпретатор.)

## Запуск сервера

Из каталога **`simple`** (где лежит папка `app`):

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Откройте в браузере:

- http://127.0.0.1:8000/ — перенаправление на Swagger  
- http://127.0.0.1:8000/docs — Swagger  
- http://127.0.0.1:8000/health — ответ `{"status":"ok"}`  
- http://127.0.0.1:8000/config/status — путь хранилища и флаг «ключ OpenAI задан»  

Загрузка только через **POST** `/upload`. Если открыть в браузере **GET** `/upload`, будет **405** — так и должно быть.

Остановка: `Ctrl+C` в терминале.

## Этап 1.2 — настройки из `.env`

```powershell
cd C:\Users\feden\pdf-book-reader\simple
Copy-Item env.example .env
# при необходимости отредактируйте .env
```

Перезапустите uvicorn. Вызовите `GET /config/status`: в `openai_configured` будет `true`, только если в `.env` непустой `OPENAI_API_KEY`. Сам ключ в ответе и в логах не показывается.

## Этап 1.3 — загрузка PDF

После `pip install -r requirements.txt` (нужен пакет `python-multipart`).

1. Запустите uvicorn из каталога `simple`.
2. Откройте http://127.0.0.1:8000/docs .
3. Разверните **POST /upload** → **Try it out** → выберите `.pdf` → **Execute**.
4. В ответе будут `file_id` и `filename`. Файл на диске: `STORAGE_PATH` из `.env` (по умолчанию `./data/files`), имя `{file_id}.pdf`.

Проверка в PowerShell через **curl** (путь к PDF свой; важно имя поля **`file=`** и **`@`** перед путём):

```powershell
curl.exe -X POST "http://127.0.0.1:8000/upload" -F "file=@C:\path\to\file.pdf"
```

Неверно: `-F "C:\...\file.pdf"` без имени поля и без `@` — curl выдаст ошибку про `-F`.

Убедитесь, что **uvicorn запущен**, иначе curl не подключится.

## Этап 1.4 — текст из PDF

Нужен пакет **PyMuPDF**: `pip install -r requirements.txt`.

1. Загрузите PDF через **POST /upload**, скопируйте `file_id` из ответа.
2. Откройте **GET /text/{file_id}** в Swagger или в браузере:  
   `http://127.0.0.1:8000/text/<file_id>`  
3. В ответе: `pages` (текст по страницам), `full_text` (всё подряд), `page_count`.

Для **отсканированных** PDF без текстового слоя строки могут быть пустыми — OCR будет в этапе 3.

## Этап 1.5 — статическая заглушка

- Каталог [`web/`](web/) раздаётся по адресу **http://127.0.0.1:8000/web/** (страница со ссылками на API).
- **http://127.0.0.1:8000/** перенаправляет на `/web/` (если каталог из `WEB_STATIC_PATH` существует; иначе на `/docs`).

После сборки React (`npm run build`) можно в `.env` задать `WEB_STATIC_PATH=путь\к\frontend\dist` и перезапустить uvicorn — тогда по `/web/` откроется фронт (когда появится этап 2).

## Этап 2.1 — каркас React + Vite

Каталог **`frontend/`** (от корня `simple`).

```powershell
cd C:\Users\feden\pdf-book-reader\simple\frontend
Copy-Item env.example .env.local
# при необходимости отредактируйте VITE_API_URL
npm install
npm run dev
```

Откройте http://127.0.0.1:5173/ — страница «Техчиталка», переключатель светлой/тёмной темы. API по умолчанию: `http://127.0.0.1:8000` (задаётся в `.env.local` как `VITE_API_URL`).

Backend должен быть запущен с CORS для dev-сервера Vite (уже включено в `app/main.py`). Для проверки сборки:

```powershell
npm run build
```

## Этап 2.2 — загрузка PDF

1. Запустите uvicorn (см. выше).
2. `npm run dev` в `frontend/`, откройте http://127.0.0.1:5173/ .
3. Нажмите **Выбрать PDF**, укажите `.pdf` — после ответа сервера отобразятся **file_id** и имя файла. Файл сохраняется в `STORAGE_PATH` (см. `.env` в `simple`).
