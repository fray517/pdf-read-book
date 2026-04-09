import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch, apiJson, BASE } from "../api";
import type { BookDetail, SegmentOut, SegmentPage } from "../types";

async function fetchBook(id: string): Promise<BookDetail> {
  return apiJson<BookDetail>(`/books/${id}`);
}

async function fetchAllSegments(bookId: string): Promise<SegmentOut[]> {
  const pageSize = 200;
  let page = 1;
  const all: SegmentOut[] = [];
  for (;;) {
    const sp = await apiJson<SegmentPage>(
      `/books/${bookId}/segments?page=${page}&page_size=${pageSize}`,
    );
    all.push(...sp.items);
    if (all.length >= sp.total || sp.items.length === 0) {
      break;
    }
    page += 1;
  }
  return all;
}

export default function Reader() {
  const { bookId = "" } = useParams<{ bookId: string }>();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [index, setIndex] = useState(0);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [audioErr, setAudioErr] = useState<string | null>(null);

  const { data: book } = useQuery({
    queryKey: ["book", bookId],
    queryFn: () => fetchBook(bookId),
    enabled: !!bookId,
    refetchInterval: (q) =>
      q.state.data?.status === "ready" || q.state.data?.status === "failed"
        ? false
        : 5000,
  });

  const { data: segments, isLoading } = useQuery({
    queryKey: ["segments", bookId],
    queryFn: () => fetchAllSegments(bookId),
    enabled: !!bookId && book?.status === "ready",
  });

  const seg = segments?.[index];
  const total = segments?.length ?? 0;

  useEffect(() => {
    if (!bookId || !seg?.has_audio || book?.status !== "ready") {
      return;
    }
    let cancelled = false;
    setAudioErr(null);

    void (async () => {
      const res = await apiFetch(
        `/books/${bookId}/segments/${seg.order_index}/audio`,
      );
      if (cancelled) {
        return;
      }
      if (!res.ok) {
        setAudioErr(await res.text());
        setBlobUrl((prev) => {
          if (prev) {
            URL.revokeObjectURL(prev);
          }
          return null;
        });
        return;
      }
      const blob = await res.blob();
      if (cancelled) {
        return;
      }
      const url = URL.createObjectURL(blob);
      setBlobUrl((prev) => {
        if (prev) {
          URL.revokeObjectURL(prev);
        }
        return url;
      });
    })();

    return () => {
      cancelled = true;
    };
  }, [bookId, seg?.order_index, seg?.has_audio, book?.status]);

  useEffect(() => {
    return () => {
      setBlobUrl((prev) => {
        if (prev) {
          URL.revokeObjectURL(prev);
        }
        return null;
      });
    };
  }, []);

  useEffect(() => {
    const el = audioRef.current;
    if (!el || !blobUrl) {
      return;
    }
    el.src = blobUrl;
    void el.play().catch(() => {
      /* автовоспроизведение может быть заблокировано */
    });
  }, [blobUrl]);

  function onEnded() {
    if (index < total - 1) {
      setIndex((i) => i + 1);
    }
  }

  function prev() {
    setIndex((i) => Math.max(0, i - 1));
  }

  function next() {
    setIndex((i) => Math.min(total - 1, i + 1));
  }

  if (!bookId) {
    return <p>Нет книги</p>;
  }

  if (book && book.status !== "ready") {
    return (
      <div className="reader">
        <Link to="/">← Библиотека</Link>
        <h1>{book.title}</h1>
        <p>Обработка: {book.status}</p>
        {book.status_message ? (
          <p className="warn">{book.status_message}</p>
        ) : null}
        <p className="hint">Статус обновляется автоматически.</p>
      </div>
    );
  }

  return (
    <div className="reader">
      <header className="reader-head">
        <Link to="/">← Библиотека</Link>
        <h1>{book?.title ?? "…"}</h1>
      </header>

      {isLoading ? <p>Загрузка сегментов…</p> : null}

      {segments && total === 0 ? (
        <p>Нет сегментов для воспроизведения.</p>
      ) : null}

      {seg ? (
        <>
          <div className="segment-meta">
            Сегмент {index + 1} / {total}
            {seg.page_no != null ? ` · стр. ${seg.page_no}` : null}
          </div>
          <article className="segment-text" key={seg.id}>
            {seg.text}
          </article>
          {audioErr ? <p className="error">{audioErr}</p> : null}
          {seg.has_audio && blobUrl ? (
            <audio ref={audioRef} controls onEnded={onEnded} />
          ) : null}
          {!seg.has_audio ? (
            <p className="warn">Для этого сегмента нет аудио.</p>
          ) : null}
        </>
      ) : null}

      <div className="player-bar">
        <button type="button" onClick={prev} disabled={index <= 0}>
          Назад
        </button>
        <button type="button" onClick={next} disabled={index >= total - 1}>
          Вперёд
        </button>
      </div>
      <p className="hint tiny">
        Бэкенд: {BASE.replace(/\/api\/v1$/, "")}
      </p>
    </div>
  );
}
