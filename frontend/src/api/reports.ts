/** 신고 건의 증거 API (docs/api-spec.md 5장). S4 증거 안내, S5 사진 검수, S6 불법주정차 사전 점검. */
import { api } from "./client";
import type { PhotoRef } from "./analyses";

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
