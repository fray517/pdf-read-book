import { useEffect, useRef, useState, type ChangeEvent } from "react";
import {
  fetchPdfText,
  getApiUrl,
  uploadPdf,
  type TextResponse,
  type UploadResult,
} from "./api";
import {
  OPENAI_TTS_VOICES,
  TTS_SPEED_DEFAULT,
  TTS_SPEED_MAX,
  TTS_SPEED_MIN,
  TTS_SPEED_STEP,
  TTS_VOICE_DEFAULT,
  type OpenAiTtsVoice,
} from "./ttsUi";
import "./App.css";

type Theme = "light" | "dark";

function loadInitialTheme(): Theme {
  const saved = localStorage.getItem("theme") as Theme | null;
  if (saved === "light" || saved === "dark") {
    return saved;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export default function App() {
  const [theme, setTheme] = useState<Theme>(loadInitialTheme);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [lastUpload, setLastUpload] = useState<UploadResult | null>(null);
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);
  const [textData, setTextData] = useState<TextResponse | null>(null);
  const [speechRate, setSpeechRate] = useState(TTS_SPEED_DEFAULT);
  const [ttsVoice, setTtsVoice] = useState<OpenAiTtsVoice>(TTS_VOICE_DEFAULT);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const apiUrl = getApiUrl();

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) {
      return;
    }
    setUploadError(null);
    setUploading(true);
    try {
      const data = await uploadPdf(file);
      setLastUpload(data);
      setTextData(null);
      setTextError(null);
    } catch (err) {
      setLastUpload(null);
      setTextData(null);
      setUploadError(
        err instanceof Error ? err.message : "Ошибка загрузки",
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleShowText() {
    if (lastUpload === null) {
      return;
    }
    setTextError(null);
    setTextLoading(true);
    try {
      const data = await fetchPdfText(lastUpload.file_id);
      setTextData(data);
    } catch (err) {
      setTextData(null);
      setTextError(
        err instanceof Error ? err.message : "Ошибка запроса текста",
      );
    } finally {
      setTextLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="top">
        <h1>Техчиталка</h1>
        <button
          type="button"
          className="theme-toggle"
          onClick={() =>
            setTheme((t) => (t === "dark" ? "light" : "dark"))
          }
          aria-label={
            theme === "dark"
              ? "Включить светлую тему"
              : "Включить тёмную тему"
          }
        >
          {theme === "dark" ? "Светлая тема" : "Тёмная тема"}
        </button>
      </header>

      <main className="content">
        <p className="lead">
          PDF: загрузка, текст, настройки озвучки (этапы 2.2–2.4).
        </p>
        <p className="meta">
          API: <code>{apiUrl}</code>
        </p>

        <section className="tts-panel" aria-labelledby="tts-heading">
          <h2 id="tts-heading" className="tts-panel-title">
            Озвучка (пока только UI)
          </h2>
          <p className="tts-hint">
            Для этапа 3: скорость и голос OpenAI TTS; на сервер пока не
            отправляются.
          </p>
          <div className="tts-row">
            <label className="tts-label" htmlFor="speech-rate">
              Скорость:{" "}
              <strong>{speechRate.toFixed(2)}</strong>×
            </label>
            <input
              id="speech-rate"
              type="range"
              className="tts-range"
              min={TTS_SPEED_MIN}
              max={TTS_SPEED_MAX}
              step={TTS_SPEED_STEP}
              value={speechRate}
              onChange={(e) =>
                setSpeechRate(Number.parseFloat(e.target.value))
              }
            />
          </div>
          <div className="tts-row">
            <label className="tts-label" htmlFor="tts-voice">
              Голос
            </label>
            <select
              id="tts-voice"
              className="tts-select"
              value={ttsVoice}
              onChange={(e) =>
                setTtsVoice(e.target.value as OpenAiTtsVoice)
              }
            >
              {OPENAI_TTS_VOICES.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>
          <pre className="tts-json" aria-label="Текущие параметры TTS">
            {JSON.stringify(
              { speech_rate: speechRate, voice: ttsVoice },
              null,
              2,
            )}
          </pre>
        </section>

        <section className="upload" aria-labelledby="upload-heading">
          <h2 id="upload-heading" className="upload-title">
            Файл
          </h2>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="visually-hidden"
            onChange={handleFileChange}
            disabled={uploading}
            aria-label="Выбрать PDF"
          />
          <button
            type="button"
            className="btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Загрузка…" : "Выбрать PDF"}
          </button>
        </section>

        {uploadError !== null ? (
          <p className="error" role="alert">
            {uploadError}
          </p>
        ) : null}

        {lastUpload !== null ? (
          <div className="upload-result">
            <p>
              <strong>file_id:</strong>{" "}
              <code className="break-all">{lastUpload.file_id}</code>
            </p>
            <p>
              <strong>Имя файла:</strong>{" "}
              <span className="break-all">{lastUpload.filename}</span>
            </p>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleShowText}
              disabled={textLoading}
            >
              {textLoading ? "Загрузка текста…" : "Показать текст"}
            </button>
          </div>
        ) : null}

        {textError !== null ? (
          <p className="error" role="alert">
            {textError}
          </p>
        ) : null}

        {textData !== null ? (
          <section className="text-panel" aria-labelledby="text-heading">
            <h2 id="text-heading" className="text-panel-title">
              Текст документа
            </h2>
            <p className="text-meta">
              Страниц: {textData.page_count} · символов:{" "}
              {textData.full_text.length}
            </p>
            <textarea
              className="text-area"
              readOnly
              rows={16}
              value={textData.full_text}
              spellCheck={false}
              aria-label="Извлечённый текст PDF"
            />
          </section>
        ) : null}

        <p className="hint">
          Backend:{" "}
          <code>uvicorn app.main:app --reload --host 127.0.0.1 --port 8000</code>{" "}
          из <code>simple</code>.
        </p>
      </main>
    </div>
  );
}
