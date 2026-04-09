export type BookStatus =
  | "uploaded"
  | "extracting"
  | "text_ready"
  | "translating"
  | "translated"
  | "tts_pending"
  | "tts_processing"
  | "ready"
  | "failed";

export interface BookListItem {
  id: string;
  title: string;
  status: BookStatus;
  source_lang: string | null;
  created_at: string;
  status_message: string | null;
}

export interface BookDetail {
  id: string;
  title: string;
  status: BookStatus;
  source_lang: string | null;
  target_lang: string;
  created_at: string;
  pages_count: number;
  segments_count: number;
  status_message: string | null;
}

export interface SegmentOut {
  id: string;
  order_index: number;
  page_no: number | null;
  text: string;
  duration_sec: number | null;
  has_audio: boolean;
}

export interface SegmentPage {
  items: SegmentOut[];
  total: number;
  page: number;
  page_size: number;
}

export type JobStatus = "pending" | "running" | "success" | "failed";

export interface JobOut {
  id: string;
  book_id: string;
  job_type: string;
  status: JobStatus;
  error_message: string | null;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}
