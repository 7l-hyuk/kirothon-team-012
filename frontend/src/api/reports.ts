/** 신고 건의 증거 API (docs/api-spec.md 5장). S4 증거 안내, S5 사진 검수, S6 불법주정차 사전 점검. */
import { api } from "./client";
import type { Category, PhotoRef, TypeId } from "./analyses";

export type ReviewStatus = "sufficient" | "insufficient" | "undetermined";

export interface SceneReview { status: ReviewStatus; message: string; retake_tip: string | null }

export interface EvidenceScene {
  scene_id: string;
  label: string;
  required: boolean;
  photo: PhotoRef | null;
  review: SceneReview | null;
}

export interface Evidence {
  report_id: string;
  label: string;
  intro: string;
  required_count: number;
  done_count: number;
  complete: boolean;
  /** false면(불법주정차) 이 앱에서 찍지 않고 사전 점검(rehearse)을 쓴다. */
  capture_in_app: boolean;
  scenes: EvidenceScene[];
}

export interface PhotoUpload {
  photo: PhotoRef & { scene_id: string | null };
  review: SceneReview | null;
  evidence: { required_count: number; done_count: number; complete: boolean };
}

export interface RehearsalCheck {
  key: "zone" | "plate_readable" | "background_included";
  status: ReviewStatus;
  label: string;
  detail: string | null;
}

export interface Rehearsal {
  passed: boolean;
  zone: string;
  checks: RehearsalCheck[];
  capture_guide: {
    title: string;
    steps: string[];
    warning: string;
    interval_seconds: number;
    interval_note: string;
  };
}

export function getEvidence(reportId: string): Promise<Evidence> {
  return api<Evidence>(`/api/reports/${reportId}/evidence`);
}

/** 사진 1장 업로드. sceneId가 있으면 AI가 그 장면의 증거로 충분한지 검수한다(4~9초). */
export function uploadPhoto(reportId: string, photo: File, sceneId?: string): Promise<PhotoUpload> {
  const form = new FormData();
  form.append("photo", photo);
  if (sceneId) form.append("scene_id", sceneId);
  return api<PhotoUpload>(`/api/reports/${reportId}/photos`, { method: "POST", body: form });
}

/** 불법주정차 사전 점검. photoId를 빼면 서버가 분석 때 올린 사진에서 고른다. 사진이 없으면 422. */
export function rehearse(reportId: string, photoId?: string): Promise<Rehearsal> {
  return api<Rehearsal>(`/api/reports/${reportId}/rehearsals`, { method: "POST", body: photoId ? { photo_id: photoId } : {} });
}

// ── 접수 안내와 신고 건 (docs/api-spec.md 4장, 6장) ────────────────

export type ActionKind = "open_link" | "confirm" | "save_photos" | "copy_text" | "submit";

export interface GuideStep {
  order: number;
  step_id: string;
  title: string;
  body: string | null;
  action: { kind: ActionKind; button_label: string; url: string | null; photos: PhotoRef[] | null; text: string | null };
  /** 같은 분석의 앞 건에서 이미 끝낸 단계 */
  skipped: boolean;
  /** false면 안전신문고 실제 화면과 대조하지 못한 안내 */
  verified: boolean;
}

export interface Guide {
  report_id: string;
  label: string;
  sequence: number;
  total: number;
  channel: { name: string; web_url: string; menu_path: string[] };
  current_step: number;
  carry_over: { label: string; message: string }[];
  steps: GuideStep[];
}

export type Tone = "default" | "shorter" | "politer";
export type ReportStatus = "preparing" | "filed" | "resolved";
export type ResultValue = "accepted" | "rejected" | "unknown";

export interface ReportPatch {
  current_step?: number;
  status?: "filed";
  receipt_number?: string | null;
  result?: ResultValue;
  result_reason?: string | null;
}

export interface Report {
  id: string;
  analysis_id: string;
  sequence: number;
  total: number;
  type_id: TypeId;
  category: Category;
  label: string;
  status: ReportStatus;
  status_label: string;
  location: { address: string | null; district: string | null; dong: string | null };
  created_at: string;
  evidence_progress: { done: number; required: number };
  current_step: number;
  step_count: number;
  channel: { name: string; menu_path: string[] };
  photos: (PhotoRef & { scene_id: string | null })[];
  draft_text: string | null;
  receipt_number: string | null;
  filed_at: string | null;
  result: ResultValue | null;
  result_reason: string | null;
  resolved_at: string | null;
  timeline: { key: string; label: string; note: string; done: boolean }[];
  case_id: string | null;
  next_report_id: string | null;
}

export interface ReportListItem {
  id: string;
  type_id: TypeId;
  category: Category;
  label: string;
  status: ReportStatus;
  status_label: string;
  district: string | null;
  dong: string | null;
  created_at: string;
  thumbnail_url: string | null;
  resumable: boolean;
}

export function getGuide(reportId: string): Promise<Guide> {
  return api<Guide>(`/api/reports/${reportId}/guide`);
}

/** 신고 문구 대필. AI를 불러 4~9초 걸린다. */
export function makeDraft(reportId: string, tone: Tone): Promise<{ text: string; tone: Tone }> {
  return api(`/api/reports/${reportId}/drafts`, { method: "POST", body: { tone } });
}

export function patchReport(reportId: string, patch: ReportPatch): Promise<Report> {
  return api<Report>(`/api/reports/${reportId}`, { method: "PATCH", body: patch });
}

export function getReport(reportId: string): Promise<Report> {
  return api<Report>(`/api/reports/${reportId}`);
}

export function listReports(status?: ReportStatus, limit = 20): Promise<{ items: ReportListItem[]; next_cursor: string | null }> {
  const q = new URLSearchParams({ limit: String(limit) });
  if (status) q.set("status", status);
  return api(`/api/reports?${q}`);
}
