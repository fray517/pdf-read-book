import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { getApiUrl, uploadPdf, type UploadResult } from "./api";
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
    } catch (err) {
      setLastUpload(null);
      setUploadError(
        err instanceof Error ? err.message : "Ошибка загрузки",
      );
    } finally {
      setUploading(false);
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
        <p className="lead">Загрузка PDF на сервер (этап 2.2).</p>
        <p className="meta">
          API: <code>{apiUrl}</code>
        </p>

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
          </div>
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
