import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { apiFetch, apiJson } from "../api";
import type { BookListItem, BookDetail } from "../types";

async function fetchBooks(): Promise<BookListItem[]> {
  return apiJson<BookListItem[]>("/books");
}

async function fetchBookDetail(id: string): Promise<BookDetail> {
  return apiJson<BookDetail>(`/books/${id}`);
}

export default function Library() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);

  const { data: books, isLoading } = useQuery({
    queryKey: ["books"],
    queryFn: fetchBooks,
  });

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) {
        throw new Error("Выберите PDF");
      }
      const fd = new FormData();
      fd.append("file", file);
      if (title.trim()) {
        fd.append("title", title.trim());
      }
      const res = await apiFetch("/books", { method: "POST", body: fd });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      return res.json() as Promise<{ book_id: string; job_id: string }>;
    },
    onSuccess: () => {
      setFile(null);
      setTitle("");
      setUploadErr(null);
      void qc.invalidateQueries({ queryKey: ["books"] });
    },
    onError: (e: Error) => setUploadErr(e.message),
  });

  function onUpload(e: FormEvent) {
    e.preventDefault();
    setUploadErr(null);
    upload.mutate();
  }

  return (
    <div className="library">
      <section className="upload-card">
        <h2>Загрузить PDF</h2>
        <p className="hint">
          Технические книги: извлечение текста, при необходимости OCR и
          перевод EN→RU, затем озвучка по сегментам с текстом на экране.
        </p>
        <form onSubmit={onUpload} className="form">
          <label>
            Название (необязательно)
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Из имени файла"
            />
          </label>
          <label>
            Файл PDF
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          {uploadErr ? <p className="error">{uploadErr}</p> : null}
          <button type="submit" disabled={upload.isPending || !file}>
            {upload.isPending ? "Загрузка…" : "Отправить"}
          </button>
        </form>
      </section>

      <section>
        <h2>Мои книги</h2>
        {isLoading ? <p>Загрузка…</p> : null}
        <ul className="book-list">
          {books?.map((b) => (
            <li key={b.id}>
              <BookRow book={b} />
            </li>
          ))}
        </ul>
        {books?.length === 0 ? <p>Пока нет книг.</p> : null}
      </section>
    </div>
  );
}

function BookRow({ book }: { book: BookListItem }) {
  const { data: detail } = useQuery({
    queryKey: ["book", book.id],
    queryFn: () => fetchBookDetail(book.id),
    refetchInterval: (q) =>
      q.state.data?.status === "ready" ||
      q.state.data?.status === "failed"
        ? false
        : 4000,
  });

  return (
    <div className="book-row">
      <div>
        <Link to={`/read/${book.id}`}>
          <strong>{book.title}</strong>
        </Link>
        <div className="meta">
          Статус: {detail?.status ?? book.status}
          {detail?.source_lang ? ` · язык: ${detail.source_lang}` : null}
          {detail?.pages_count != null ? ` · стр.: ${detail.pages_count}` : null}
          {detail?.segments_count != null
            ? ` · сегментов: ${detail.segments_count}`
            : null}
        </div>
        {detail?.status_message ? (
          <div className="warn">{detail.status_message}</div>
        ) : null}
      </div>
      <div className="row-actions">
        {detail?.status === "ready" ? (
          <Link className="button" to={`/read/${book.id}`}>
            Читать
          </Link>
        ) : null}
      </div>
    </div>
  );
}
