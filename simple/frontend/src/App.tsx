import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import {
  detectLanguage,
  fetchPdfText,
  fetchSegments,
  fetchTranslate,
  getApiUrl,
  getAudioUrl,
  uploadPdf,
  type SegmentsResult,
  type TextResponse,
  type TranslateResult,
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
  const [langLoading, setLangLoading] = useState(false);
  const [langError, setLangError] = useState<string | null>(null);
  const [detectedLang, setDetectedLang] = useState<string | null>(null);
  const [translateLoading, setTranslateLoading] = useState(false);
  const [translateError, setTranslateError] = useState<string | null>(null);
  const [translateData, setTranslateData] = useState<TranslateResult | null>(
    null,
  );
  const [useOcr, setUseOcr] = useState(false);
  const [useRuSegments, setUseRuSegments] = useState(false);
  const [segmentsLoading, setSegmentsLoading] = useState(false);
  const [segmentsError, setSegmentsError] = useState<string | null>(null);
  const [segmentsData, setSegmentsData] = useState<SegmentsResult | null>(
    null,
  );
  const [segmentParams, setSegmentParams] = useState<{
    ocr: boolean;
    useRu: boolean;
  } | null>(null);
  const [narrateLoading, setNarrateLoading] = useState(false);
  const [narrateError, setNarrateError] = useState<string | null>(null);
  const [readerIndex, setReaderIndex] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const advancePlaybackRef = useRef(false);

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
      setDetectedLang(null);
      setLangError(null);
      setTranslateData(null);
      setTranslateError(null);
      setSegmentsData(null);
      setSegmentsError(null);
      setSegmentParams(null);
      setReaderIndex(0);
      setNarrateError(null);
    } catch (err) {
      setLastUpload(null);
      setTextData(null);
      setDetectedLang(null);
      setLangError(null);
      setTranslateData(null);
      setTranslateError(null);
      setSegmentsData(null);
      setSegmentsError(null);
      setSegmentParams(null);
      setReaderIndex(0);
      setNarrateError(null);
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
      const data = await fetchPdfText(lastUpload.file_id, {
        ocr: useOcr,
      });
      setTextData(data);
      setDetectedLang(null);
      setLangError(null);
      setTranslateData(null);
      setTranslateError(null);
      setSegmentsData(null);
      setSegmentsError(null);
      setSegmentParams(null);
      setReaderIndex(0);
      setNarrateError(null);
    } catch (err) {
      setTextData(null);
      setTextError(
        err instanceof Error ? err.message : "Ошибка запроса текста",
      );
    } finally {
      setTextLoading(false);
    }
  }

  async function handleDetectLanguage() {
    if (textData === null) {
      return;
    }
    setLangError(null);
    setLangLoading(true);
    try {
      const { lang } = await detectLanguage(textData.full_text);
      setDetectedLang(lang);
    } catch (err) {
      setDetectedLang(null);
      setLangError(
        err instanceof Error ? err.message : "Ошибка определения языка",
      );
    } finally {
      setLangLoading(false);
    }
  }

  async function handleFetchSegments() {
    if (lastUpload === null) {
      return;
    }
    setSegmentsError(null);
    setSegmentsLoading(true);
    try {
      const data = await fetchSegments(lastUpload.file_id, {
        ocr: useRuSegments ? false : useOcr,
        useRu: useRuSegments,
      });
      setSegmentsData(data);
      setSegmentParams({
        ocr: useRuSegments ? false : useOcr,
        useRu: useRuSegments,
      });
      setReaderIndex(0);
    } catch (err) {
      setSegmentsData(null);
      setSegmentParams(null);
      setSegmentsError(
        err instanceof Error ? err.message : "Ошибка сегментов",
      );
    } finally {
      setSegmentsLoading(false);
    }
  }

  async function handleTranslate(refresh: boolean) {
    if (lastUpload === null) {
      return;
    }
    setTranslateError(null);
    setTranslateLoading(true);
    try {
      const data = await fetchTranslate(lastUpload.file_id, refresh);
      setTranslateData(data);
    } catch (err) {
      setTranslateData(null);
      setTranslateError(
        err instanceof Error ? err.message : "Ошибка перевода",
      );
    } finally {
      setTranslateLoading(false);
    }
  }

  async function handleNarrate() {
    if (lastUpload === null) {
      return;
    }
    setNarrateError(null);
    setNarrateLoading(true);
    try {
      const text = await fetchPdfText(lastUpload.file_id, {
        ocr: useOcr,
      });
      setTextData(text);
      const trimmed = text.full_text.trim();
      let lang = "ru";
      if (trimmed.length >= 20) {
        const { lang: detected } = await detectLanguage(text.full_text);
        lang = detected;
      }
      setDetectedLang(lang);
      let segOcr = useOcr;
      let segUseRu = false;
      if (trimmed.length >= 20 && lang !== "ru") {
        const tr = await fetchTranslate(lastUpload.file_id, false);
        setTranslateData(tr);
        segUseRu = true;
        segOcr = false;
      } else {
        setTranslateData(null);
        setTranslateError(null);
      }
      setUseRuSegments(segUseRu);
      const data = await fetchSegments(lastUpload.file_id, {
        ocr: segOcr,
        useRu: segUseRu,
      });
      setSegmentsData(data);
      setSegmentParams({
        ocr: segOcr,
        useRu: segUseRu,
      });
      setSegmentsError(null);
      setReaderIndex(0);
    } catch (err) {
      setNarrateError(
        err instanceof Error ? err.message : "Ошибка подготовки озвучки",
      );
    } finally {
      setNarrateLoading(false);
    }
  }

  const segmentCount = segmentsData?.segment_count ?? 0;
  const safeReaderIndex =
    segmentCount > 0
      ? Math.min(readerIndex, Math.max(0, segmentCount - 1))
      : 0;

  useEffect(() => {
    if (segmentCount > 0 && readerIndex > segmentCount - 1) {
      setReaderIndex(segmentCount - 1);
    }
  }, [segmentCount, readerIndex]);

  useEffect(() => {
    const el = audioRef.current;
    if (
      el === null ||
      lastUpload === null ||
      segmentParams === null ||
      segmentsData === null ||
      segmentCount === 0
    ) {
      return;
    }
    const url = getAudioUrl(lastUpload.file_id, safeReaderIndex, {
      ocr: segmentParams.ocr,
      useRu: segmentParams.useRu,
      voice: ttsVoice,
      speed: speechRate,
    });
    el.pause();
    el.src = url;
    el.load();
    const onCanPlay = () => {
      if (advancePlaybackRef.current) {
        advancePlaybackRef.current = false;
        void el.play().catch(() => {});
      }
    };
    el.addEventListener("canplay", onCanPlay, { once: true });
  }, [
    lastUpload?.file_id,
    segmentParams,
    segmentsData?.segment_count,
    segmentCount,
    safeReaderIndex,
    ttsVoice,
    speechRate,
  ]);

  useEffect(() => {
    const el = audioRef.current;
    if (el === null || segmentCount === 0) {
      return;
    }
    const onEnded = () => {
      setReaderIndex((i) => {
        if (i < segmentCount - 1) {
          advancePlaybackRef.current = true;
          return i + 1;
        }
        return i;
      });
    };
    el.addEventListener("ended", onEnded);
    return () => {
      el.removeEventListener("ended", onEnded);
    };
  }, [segmentCount]);

  function goReaderPrev() {
    advancePlaybackRef.current = false;
    setReaderIndex((i) => Math.max(0, i - 1));
  }

  function goReaderNext() {
    advancePlaybackRef.current = false;
    setReaderIndex((i) =>
      segmentCount > 0 ? Math.min(segmentCount - 1, i + 1) : i,
    );
  }

  const currentSegment = segmentsData?.segments.find(
    (s) => s.index === safeReaderIndex,
  );
  const currentSegmentText = currentSegment?.text ?? "";

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
          PDF: загрузка, текст, перевод, сегменты, читалка (2.x–3.6).
        </p>
        <p className="meta">
          API: <code>{apiUrl}</code>
        </p>

        <section className="tts-panel" aria-labelledby="tts-heading">
          <h2 id="tts-heading" className="tts-panel-title">
            Озвучка (OpenAI TTS)
          </h2>
          <p className="tts-hint">
            Скорость и голос передаются в <code>GET /audio/…</code> (этап 3.5–
            3.6).
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
            <label className="ocr-option">
              <input
                type="checkbox"
                checked={useOcr}
                onChange={(e) => setUseOcr(e.target.checked)}
                disabled={textLoading}
              />{" "}
              OCR для сканов (OpenAI Vision, этап 3.3)
            </label>
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

        {lastUpload !== null ? (
          <section
            className="reader-panel"
            aria-labelledby="reader-heading"
          >
            <h2 id="reader-heading" className="reader-panel-title">
              Читалка (3.6)
            </h2>
            <p className="tts-hint">
              Кнопка «Озвучить»: извлечение текста (как у «Показать текст», с
              учётом OCR), язык, при необходимости перевод, сегменты. Плеер
              показывает текст текущего фрагмента; после окончания трека
              воспроизводится следующий сегмент.
            </p>
            <button
              type="button"
              className="btn-primary"
              onClick={handleNarrate}
              disabled={narrateLoading}
            >
              {narrateLoading ? "Подготовка озвучки…" : "Озвучить"}
            </button>
            {narrateError !== null ? (
              <p className="error" role="alert">
                {narrateError}
              </p>
            ) : null}
            {segmentParams !== null &&
            segmentsData !== null &&
            segmentCount > 0 ? (
              <div className="reader-body">
                <p className="reader-meta" aria-live="polite">
                  Сегмент {safeReaderIndex + 1} из {segmentCount}
                  {currentSegment !== undefined &&
                  currentSegment.page_no > 0
                    ? ` · стр. ${currentSegment.page_no}`
                    : null}
                </p>
                <div
                  className="reader-text-block"
                  aria-label="Текст текущего сегмента"
                >
                  {currentSegmentText}
                </div>
                <audio
                  ref={audioRef}
                  className="reader-audio"
                  controls
                  preload="metadata"
                  aria-label="Озвучка текущего сегмента"
                />
                <div className="reader-nav">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={goReaderPrev}
                    disabled={safeReaderIndex <= 0}
                  >
                    Назад
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={goReaderNext}
                    disabled={safeReaderIndex >= segmentCount - 1}
                  >
                    Вперёд
                  </button>
                </div>
              </div>
            ) : null}
            {segmentParams !== null &&
            segmentsData !== null &&
            segmentCount === 0 ? (
              <p className="tts-hint">Нет сегментов для озвучки.</p>
            ) : null}
          </section>
        ) : null}

        {lastUpload !== null ? (
          <section
            className="translate-panel"
            aria-labelledby="translate-heading"
          >
            <h2 id="translate-heading" className="translate-panel-title">
              Перевод на русский (3.2)
            </h2>
            <p className="tts-hint">
              Текст снова извлекается из PDF на сервере; для не‑русского
              нужен <code>OPENAI_API_KEY</code> в <code>simple/.env</code>.
            </p>
            <div className="lang-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleTranslate(false)}
                disabled={translateLoading}
              >
                {translateLoading ? "Перевод…" : "Перевести на русский"}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleTranslate(true)}
                disabled={translateLoading}
              >
                Обновить перевод
              </button>
            </div>
            {translateError !== null ? (
              <p className="error" role="alert">
                {translateError}
              </p>
            ) : null}
            {translateData !== null ? (
              <>
                <p className="text-meta">
                  Исходный язык: <code>{translateData.source_lang}</code>
                  {translateData.cached ? " · из кэша (_ru.txt)" : null}
                </p>
                <textarea
                  className="text-area"
                  readOnly
                  rows={12}
                  value={translateData.text}
                  spellCheck={false}
                  aria-label="Перевод на русский"
                />
              </>
            ) : null}
          </section>
        ) : null}

        {lastUpload !== null ? (
          <section
            className="segments-panel"
            aria-labelledby="segments-heading"
          >
            <h2 id="segments-heading" className="translate-panel-title">
              Сегменты для озвучки (3.4)
            </h2>
            <p className="tts-hint">
              Абзацы и лимит длины на сегмент (для TTS). Для русского текста
              включите опцию перевода — нужен файл <code>_ru.txt</code>.
            </p>
            <label className="ocr-option">
              <input
                type="checkbox"
                checked={useRuSegments}
                onChange={(e) => setUseRuSegments(e.target.checked)}
                disabled={segmentsLoading}
              />{" "}
              Брать текст из перевода (_ru.txt)
            </label>
            {useRuSegments ? null : (
              <label className="ocr-option">
                <input
                  type="checkbox"
                  checked={useOcr}
                  onChange={(e) => setUseOcr(e.target.checked)}
                  disabled={segmentsLoading}
                />{" "}
                Как при «Показать текст»: OCR для сканов
              </label>
            )}
            <button
              type="button"
              className="btn-secondary"
              onClick={handleFetchSegments}
              disabled={segmentsLoading}
            >
              {segmentsLoading ? "Сегменты…" : "Показать сегменты"}
            </button>
            {segmentsError !== null ? (
              <p className="error" role="alert">
                {segmentsError}
              </p>
            ) : null}
            {segmentsData !== null ? (
              <>
                <p className="text-meta">
                  Сегментов: {segmentsData.segment_count} · источник:{" "}
                  <code>{segmentsData.source}</code> · лимит{" "}
                  {segmentsData.max_chars} симв.
                </p>
                <pre
                  className="tts-json"
                  aria-label="Список сегментов (превью)"
                >
                  {JSON.stringify(
                    {
                      ...segmentsData,
                      segments: segmentsData.segments.slice(0, 20),
                      _preview_remaining:
                        segmentsData.segment_count > 20
                          ? segmentsData.segment_count - 20
                          : undefined,
                    },
                    null,
                    2,
                  )}
                </pre>
              </>
            ) : null}
          </section>
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
              {textData.ocr_pages !== undefined &&
              textData.ocr_pages.length > 0 ? (
                <>
                  {" "}
                  · OCR страниц:{" "}
                  {textData.ocr_pages.join(", ")}
                </>
              ) : null}
            </p>
            <textarea
              className="text-area"
              readOnly
              rows={16}
              value={textData.full_text}
              spellCheck={false}
              aria-label="Извлечённый текст PDF"
            />
            <div className="lang-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={handleDetectLanguage}
                disabled={langLoading || textData.full_text.length < 20}
              >
                {langLoading ? "Определение…" : "Определить язык"}
              </button>
              {detectedLang !== null ? (
                <p className="lang-result">
                  Язык (ISO 639-1):{" "}
                  <code>{detectedLang}</code>
                </p>
              ) : null}
            </div>
            {langError !== null ? (
              <p className="error" role="alert">
                {langError}
              </p>
            ) : null}
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
