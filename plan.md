# План: простая читалка PDF с озвучкой (с нуля, по шагам)

Цель: **не усложнять**. Сначала минимальный рабочий каркас, потом функции по одной. После **каждого подэтапа** — можно запустить и проверить.

**Принципы:**

- Один компьютер, **один пользователь**, без логина.
- **Backend:** Python 3.11 + FastAPI, всё в одной папке проекта.
- **Frontend:** React (Vite) — когда дойдём до этапа 2.
- Секреты — в `.env` (у вас он локальный); в репозитории только `env.example`.

---

## Этап 1 — Backend (локально, без авторизации)

*Здесь только API и файлы на диске. Браузер пока можно заменить Swagger (`/docs`) или `curl`.*

### 1.1 Каркас проекта

- Папка `app/`, `main.py`, зависимости в `requirements.txt`.
- `GET /health` → `{"status": "ok"}`.
- Запуск: `uvicorn main:app --reload` (из папки backend или как договоримся).

**Готово, если:** открываете `/docs`, видите один эндпоинт, ответ 200.

**Сделано:** каталог [`simple/`](simple/) — запуск `uvicorn app.main:app` (см. [`simple/README.md`](simple/README.md)).

### 1.2 Настройки из `.env`

- `env.example`: например `OPENAI_API_KEY=`, `STORAGE_PATH=./data/files`.
- Загрузка через `python-dotenv` + одна функция `get_settings()`.

**Готово, если:** ключ читается (не логировать ключ в консоль).

**Сделано:** [`simple/app/config.py`](simple/app/config.py), [`simple/env.example`](simple/env.example), эндпоинт `GET /config/status`.

### 1.3 Загрузка одного PDF (без обработки)

- `POST /upload` — один файл в теле, сохранить под уникальным именем в `STORAGE_PATH`.
- Ответ: `{ "file_id": "...", "filename": "..." }`.

**Готово, если:** файл появляется на диске, в ответе есть id.

**Сделано:** `POST /upload`, [`simple/app/schemas.py`](simple/app/schemas.py), сохранение в `STORAGE_PATH` как `{uuid}.pdf`.

### 1.4 Извлечение текста из PDF (простой случай)

- Библиотека вроде PyMuPDF: текст со **всех страниц** в одну строку или список по страницам.
- `GET /text/{file_id}` — вернуть извлечённый текст (или JSON с полями по страницам).

**Готово, если:** для «нормального» PDF с текстом видите текст в ответе.

**Сделано:** `GET /text/{file_id}`, PyMuPDF в [`simple/app/services/pdf_text.py`](simple/app/services/pdf_text.py).

*Отдельно позже (этап 3): сканы без текста → OCR.*

### 1.5 (Опционально до этапа 2) Статика фронта или заглушка

- Либо `FastAPI.mount` на `frontend/dist`, либо пропускаем до этапа 2.

**Сделано:** каталог [`simple/web/`](simple/web/), раздача на префиксе `/web`, `GET /` → `/web/` или `/docs`; переменная `WEB_STATIC_PATH` в [`simple/app/config.py`](simple/app/config.py).

---

## Этап 2 — Frontend: загрузка, тема, текст, скорость, голос

*Минимальный UI, без логина. Общается только с вашим локальным API.*

### 2.1 Каркас React + Vite

- Одна страница, тёмная/светлая тема переключается (CSS variables или готовый переключатель).
- Переменная `VITE_API_URL=http://127.0.0.1:8000` (или прокси в `vite.config`).

**Готово, если:** `npm run dev` открывается страница, тема переключается.

**Сделано:** [`simple/frontend/`](simple/frontend/) — Vite + React, тема (`data-theme` + `localStorage`), [`simple/frontend/env.example`](simple/frontend/env.example), `src/api.ts`; CORS для `localhost:5173` / `127.0.0.1:5173` в [`simple/app/main.py`](simple/app/main.py).

### 2.2 Загрузка PDF

- Кнопка + `input type=file`, `POST /upload` через `fetch` / `FormData`.
- Показать `file_id` и имя файла.

**Готово, если:** тот же файл лежит на сервере, id на экране.

**Сделано:** [`simple/frontend/src/App.tsx`](simple/frontend/src/App.tsx) — кнопка, скрытый `input type=file`, `POST /upload` через `fetch`/`FormData`; [`simple/frontend/src/api.ts`](simple/frontend/src/api.ts) — `uploadPdf()`.

### 2.3 Окно текста

- После загрузки (или по кнопке «Показать текст») — `GET /text/{file_id}`, вывод в `<textarea>` или блок с прокруткой.

**Готово, если:** видите извлечённый текст из 1.4.

**Сделано:** кнопка «Показать текст», `GET /text/{file_id}` через [`fetchPdfText`](simple/frontend/src/api.ts), вывод `full_text` в [`<textarea>`](simple/frontend/src/App.tsx).

### 2.4 Скорость и голос (пока только UI)

- Слайдер или селект «скорость» (значения для будущего TTS, например 0.8–1.2).
- Селект «голос» (список имён голосов OpenAI — захардкодить те же, что будут на бэкенде).
- Состояние хранить в React (`useState`); **на сервер пока не обязательно слать** — подключим на этапе 3 вместе с озвучкой.

**Готово, если:** значения меняются, отображаются на экране (можно вывести JSON снизу для проверки).

**Сделано:** слайдер скорости 0.8–1.2, селект голосов OpenAI TTS ([`ttsUi.ts`](simple/frontend/src/ttsUi.ts)), JSON-снимок состояния в [`App.tsx`](simple/frontend/src/App.tsx).

---

## Этап 3 — Язык, перевод, OCR, озвучка

*Подключаем OpenAI по шагам, чтобы не смешивать всё сразу.*

### 3.1 Определение языка

- На бэкенде: взять начало текста → запрос к модели (или маленькая библиотека) → код языка `en` / `ru` / др.
- Эндпоинт: `POST /detect-language` с телом `{ "text": "..." }` → `{ "lang": "en" }`.

**Готово, если:** для короткого русского и английского фрагмента ответ правдоподобный.

**Сделано:** `POST /detect-language` ([`simple/app/main.py`](simple/app/main.py)), [`langdetect`](simple/app/services/detect_language.py) по началу текста; на фронте кнопка после текста ([`App.tsx`](simple/frontend/src/App.tsx)), [`detectLanguage`](simple/frontend/src/api.ts).

### 3.2 Перевод на русский (если не русский)

- Если язык не `ru` — один запрос к Chat Completions: перевод технического текста, сохранить результат (в памяти или файл `..._ru.txt` рядом с PDF).
- Эндпоинт: `POST /translate/{file_id}` → текст на русском.

**Готово, если:** для английского абзаца получаете русский текст в ответе/API.

**Сделано:** `POST /translate/{file_id}` ([`main.py`](simple/app/main.py)), кэш `{file_id}_ru.txt`, перевод через OpenAI при языке ≠ `ru` ([`translate_ru.py`](simple/app/services/translate_ru.py)); фронт — [`fetchTranslate`](simple/frontend/src/api.ts), блок в [`App.tsx`](simple/frontend/src/App.tsx).

### 3.3 OCR для «пустых» страниц (сканы)

- Если с страницы мало текста — картинка страницы → Vision API → текст.
- Встроить в пайплайн после 1.4 (сначала одна тестовая страница).

**Готово, если:** один скан-пример даёт текст.

**Сделано:** параметр **`GET /text/{file_id}?ocr=true`** — если на странице мало символов слоя текста (порог ~40), PNG → Vision ([`ocr_vision.py`](simple/app/services/ocr_vision.py), [`pdf_ocr.py`](simple/app/services/pdf_ocr.py)); в ответе **`ocr_pages`**. На фронте чекбокс «OCR для сканов» ([`App.tsx`](simple/frontend/src/App.tsx), [`fetchPdfText`](simple/frontend/src/api.ts)).

### 3.4 Разбиение на сегменты для озвучки

- Правила: абзацы, максимум N символов на сегмент (лимит TTS).
- Внутренний объект/файл: список сегментов.

**Готово, если:** для длинного текста получаете массив сегментов (можно отдать `GET /segments/{file_id}`).

**Сделано:** [`GET /segments/{file_id}`](simple/app/main.py) (`ocr`, `use_ru`), логика в [`segmentation.py`](simple/app/services/segmentation.py) (лимит ~3500 симв., абзацы); фронт — [`fetchSegments`](simple/frontend/src/api.ts), блок в [`App.tsx`](simple/frontend/src/App.tsx).

### 3.5 Озвучка (OpenAI TTS)

- Для каждого сегмента — запрос TTS, сохранить mp3 (кэш рядом с хранилищем: `data/audio/{file_id}/{index}_{voice}_{speed}.mp3`, скорость в имени с подчёркиванием вместо точки).
- Эндпоинт: `GET /audio/{file_id}/{segment_index}` — отдача `audio/mpeg`; query: **`ocr`**, **`use_ru`**, **`voice`** (по умолчанию `alloy`), **`speed`** (0.25–4.0).

**Готово, если:** хотя бы один сегмент играется в браузере (`<audio src=...>`).

**Сделано:** [`GET /audio/{file_id}/{segment_index}`](simple/app/main.py), синтез и кэш в [`tts_mp3.py`](simple/app/services/tts_mp3.py), общая сегментация с `/segments` в [`segment_pipeline.py`](simple/app/services/segment_pipeline.py); фронт — [`getAudioUrl`](simple/frontend/src/api.ts), превью первых 5 сегментов в [`App.tsx`](simple/frontend/src/App.tsx).

### 3.6 Связка с фронтом (этап 2)

- Кнопка «Озвучить»: вызов пайплайна (язык → перевод при необходимости → сегменты → TTS).
- Плеер: текущий сегмент + синхронный текст (как раньше в ТЗ — **по сегментам**, не пословно).

**Готово, если:** полный сценарий: загрузка PDF → текст → озвучка с экраном.

**Сделано:** на фронте кнопка **«Озвучить»** ([`App.tsx`](simple/frontend/src/App.tsx)) — `GET /text` (с тем же OCR, что у «Показать текст») → `POST /detect-language` (если ≥ 20 символов; иначе считаем русский и перевод не делаем) → при языке ≠ `ru` — `POST /translate` и сегменты из `_ru.txt` → `GET /segments`; один `<audio>` с автопереходом на следующий сегмент по событию `ended`, блок текста текущего сегмента, кнопки «Назад»/«Вперёд». Ручной сценарий «Показать сегменты» по-прежнему заполняет тот же плеер.

---

## Что сознательно отложено (после базы)

- Регистрация, JWT, несколько пользователей.
- PostgreSQL, Redis, Celery — только если решите выкладывать в сеть или грузить тяжёлые книги в фоне.
- Docker — по желанию, не обязателен для обучения.

---

## Порядок работы в репозитории

1. Делать **один подэтап за раз**.
2. В конце подэтапа — короткая заметка в `CHANGELOG.md` или коммит с сообщением вида: `этап 1.3: загрузка PDF`.
3. Если текущий код мешает — можно завести папку `simple/` или новую ветку `simple-app` и переносить туда только то, что по плану.

Когда будете готовы к **этапу 1.1**, напишите — можно выписать конкретные файлы и команды PowerShell под ваш каталог проекта.
