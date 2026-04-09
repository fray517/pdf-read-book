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
  ocr_pages?: number[];
};

/** GET /text/{file_id} — извлечённый текст PDF. */
export async function fetchPdfText(
  fileId: string,
  options?: { ocr?: boolean },
): Promise<TextResponse> {
  const enc = encodeURIComponent(fileId);
  const ocr = options?.ocr === true ? "?ocr=true" : "";
  const res = await fetch(`${getApiUrl()}/text/${enc}${ocr}`);
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

export type SegmentItem = {
  index: number;
  page_no: number;
  text: string;
  char_count: number;
};

export type SegmentsResult = {
  file_id: string;
  source: string;
  max_chars: number;
  segment_count: number;
  segments: SegmentItem[];
};

/** GET /segments/{file_id} — сегменты для TTS. */
export async function fetchSegments(
  fileId: string,
  options?: { ocr?: boolean; useRu?: boolean },
): Promise<SegmentsResult> {
  const enc = encodeURIComponent(fileId);
  const p = new URLSearchParams();
  if (options?.ocr === true) {
    p.set("ocr", "true");
  }
  if (options?.useRu === true) {
    p.set("use_ru", "true");
  }
  const q = p.toString();
  const suffix = q !== "" ? `?${q}` : "";
  const res = await fetch(`${getApiUrl()}/segments/${enc}${suffix}`);
  if (!res.ok) {
    throw new Error(await errorMessageFromResponse(res));
  }
  return res.json() as Promise<SegmentsResult>;
}

/** GET /audio/{file_id}/{segment_index} — URL для <audio src>. */
export function getAudioUrl(
  fileId: string,
  segmentIndex: number,
  options: {
    ocr?: boolean;
    useRu?: boolean;
    voice: string;
    speed: number;
  },
): string {
  const p = new URLSearchParams();
  if (options.useRu === true) {
    p.set("use_ru", "true");
  } else if (options.ocr === true) {
    p.set("ocr", "true");
  }
  p.set("voice", options.voice);
  p.set("speed", String(options.speed));
  const enc = encodeURIComponent(fileId);
  const q = p.toString();
  return `${getApiUrl()}/audio/${enc}/${segmentIndex}?${q}`;
}
