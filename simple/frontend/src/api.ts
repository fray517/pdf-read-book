/** Базовый URL FastAPI (этап 2.1). */

export function getApiUrl(): string {
  const u = import.meta.env.VITE_API_URL as string | undefined;
  if (u !== undefined && u !== "") {
    return u.replace(/\/$/, "");
  }
  return "http://127.0.0.1:8000";
}

async function errorMessageFromResponse(res: Response): Promise<string> {
  const fallback = res.statusText;
  try {
    const data: unknown = await res.json();
    if (typeof data !== "object" || data === null || !("detail" in data)) {
      return fallback;
    }
    const d = (data as { detail: unknown }).detail;
    if (typeof d === "string") {
      return d;
    }
    if (Array.isArray(d)) {
      const parts = d.map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      });
      return parts.join("; ");
    }
    return JSON.stringify(d);
  } catch {
    return fallback;
  }
}

export type UploadResult = {
  file_id: string;
  filename: string;
};

/** POST /upload — поле формы `file`, как в FastAPI. */
export async function uploadPdf(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${getApiUrl()}/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(await errorMessageFromResponse(res));
  }
  return res.json() as Promise<UploadResult>;
}

export type PageText = {
  page_no: number;
  text: string;
};

/** Ответ GET /text/{file_id} (как в simple/app/schemas.py). */
export type TextResponse = {
  file_id: string;
  page_count: number;
  pages: PageText[];
  full_text: string;
};

/** GET /text/{file_id} — извлечённый текст PDF. */
export async function fetchPdfText(fileId: string): Promise<TextResponse> {
  const enc = encodeURIComponent(fileId);
  const res = await fetch(`${getApiUrl()}/text/${enc}`);
  if (!res.ok) {
    throw new Error(await errorMessageFromResponse(res));
  }
  return res.json() as Promise<TextResponse>;
}

export type DetectLanguageResult = {
  lang: string;
};

/** Как `app/services/detect_language.py` — анализ только начала. */
const DETECT_LANGUAGE_SAMPLE_CHARS = 2000;

/** POST /detect-language — тело `{ "text": "..." }`. */
export async function detectLanguage(
  text: string,
): Promise<DetectLanguageResult> {
  const safe = text == null ? "" : String(text);
  const sample = safe.slice(0, DETECT_LANGUAGE_SAMPLE_CHARS);
  const res = await fetch(`${getApiUrl()}/detect-language`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: sample }),
  });
  if (!res.ok) {
    throw new Error(await errorMessageFromResponse(res));
  }
  return res.json() as Promise<DetectLanguageResult>;
}

export type TranslateResult = {
  file_id: string;
  text: string;
  source_lang: string;
  cached: boolean;
};

/** POST /translate/{file_id} — перевод на русский, кэш в *_ru.txt. */
export async function fetchTranslate(
  fileId: string,
  refresh = false,
): Promise<TranslateResult> {
  const enc = encodeURIComponent(fileId);
  const q = refresh ? "?refresh=true" : "";
  const res = await fetch(`${getApiUrl()}/translate/${enc}${q}`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(await errorMessageFromResponse(res));
  }
  return res.json() as Promise<TranslateResult>;
}
