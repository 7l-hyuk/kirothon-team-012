/** 상황 분석 API (docs/api-spec.md 3장). S1 보내기 → S2 분석 중 → S3 항목 선택. */
import { api } from "./client";

export type TypeId = "illegal_parking" | "trash_dumping" | "illegal_ad" | "facility_damage";
export type Category = "report" | "complaint";

export interface PhotoRef { id: string; url: string }

export interface AnalysisItem {
  type_id: TypeId;
  category: Category;
  label: string;
  subtitle: string;
  reason: string;
  detail: { zone?: string };
}

export interface Analysis {
  id: string;
  created_at: string;
  input: { text: string | null; photos: PhotoRef[] };
  reportable: boolean;
  summary: string;
  items: AnalysisItem[];
  unsupported_items: { label: string; message: string }[];
  not_reportable: { title: string; message: string; basis: string } | null;
  location: { address: string | null; district: string | null; dong: string | null };
  emergency: boolean;
  disclaimer: string;
}

export interface ReportRef { id: string; type_id: TypeId; sequence: number; status: "preparing" | "filed" | "resolved" }
export interface CreateReportsResponse { analysis_id: string; total: number; reports: ReportRef[] }

/** 서버 제한과 같은 값. 보내기 전에 막아 쓸데없는 업로드를 줄인다. */
export const LIMITS = {
  textMax: 500,
  photoMax: 4,
  photoBytes: 10 * 1024 * 1024,
  photoTypes: ["image/jpeg", "image/png", "image/webp"],
} as const;

/** 사진·글 분석. AI를 불러 4~9초 걸린다. */
export function createAnalysis(text: string, photos: File[], signal?: AbortSignal): Promise<Analysis> {
  const form = new FormData();
  if (text) form.append("text", text);
  photos.forEach((f) => form.append("photos", f));
  return api<Analysis>("/api/analyses", { method: "POST", body: form, signal });
}

/** S3에서 고른 항목으로 신고 건 생성. 배열 순서가 진행 순서(sequence)다. */
export function createReports(analysisId: string, typeIds: TypeId[]): Promise<CreateReportsResponse> {
  return api<CreateReportsResponse>(`/api/analyses/${analysisId}/reports`, { method: "POST", body: { type_ids: typeIds } });
}
