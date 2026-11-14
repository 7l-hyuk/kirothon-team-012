/** 사례 공유와 사례 API (docs/api-spec.md 7장, 8장). S12 목록, S13 상세, S14 공유 동의. */
import { api } from "./client";
import type { PhotoRef, TypeId } from "./analyses";

export interface CaseListItem {
  id: string;
  title: string;
  type_id: TypeId;
  type_label: string;
  result_label: string;
  district: string | null;
  like_count: number;
  /** 사진이 없으면(예시 사례) null */
  cover_url: string | null;
}

export interface CaseDetail {
  id: string;
  title: string;
  type_id: TypeId;
  type_label: string;
  result_label: string;
  district: string | null;
  period: string;
  sections: { heading: string; body: string; photos: PhotoRef[] }[];
  like_count: number;
  liked_by_me: boolean;
  is_mine: boolean;
  created_at: string;
}

export interface CasePreview {
  title: string;
  type_id: TypeId;
  result_label: string;
  district: string | null;
  period: string;
  sections: { heading: string; body: string }[];
  photos: PhotoRef[];
  removed: { label: string; treatment: string }[];
  photo_notice: string;
}

export function listCases(type?: TypeId): Promise<{ items: CaseListItem[]; next_cursor: string | null }> {
  return api(`/api/cases${type ? `?type=${type}` : ""}`);
}

export function getCase(id: string): Promise<CaseDetail> {
  return api<CaseDetail>(`/api/cases/${id}`);
}

export function setLike(id: string, on: boolean): Promise<{ like_count: number; liked_by_me: boolean }> {
  return api(`/api/cases/${id}/like`, { method: on ? "PUT" : "DELETE" });
}

/** 공유 미리보기. 처음 부를 때 AI가 글을 써서 10초쯤 걸리고, 다음부터는 저장된 글이 바로 온다. 접수 전이면 409. */
export function getCasePreview(reportId: string): Promise<CasePreview> {
  return api<CasePreview>(`/api/reports/${reportId}/case-preview`);
}

export function shareCase(reportId: string): Promise<CaseDetail> {
  return api<CaseDetail>(`/api/reports/${reportId}/case`, { method: "POST", body: { consent: true } });
}

export function unshareCase(reportId: string): Promise<void> {
  return api<void>(`/api/reports/${reportId}/case`, { method: "DELETE" });
}
