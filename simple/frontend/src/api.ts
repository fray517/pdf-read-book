/** Базовый URL FastAPI (этап 2.1). */

export function getApiUrl(): string {
  const u = import.meta.env.VITE_API_URL as string | undefined;
  if (u !== undefined && u !== "") {
    return u.replace(/\/$/, "");
  }
  return "http://127.0.0.1:8000";
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
    let message = res.statusText;
    try {
      const data: unknown = await res.json();
      if (
        typeof data === "object" &&
        data !== null &&
        "detail" in data
      ) {
        const d = (data as { detail: unknown }).detail;
        message =
          typeof d === "string"
            ? d
            : JSON.stringify(d);
      }
    } catch {
      /* оставляем statusText */
    }
    throw new Error(message);
  }
  return res.json() as Promise<UploadResult>;
}
