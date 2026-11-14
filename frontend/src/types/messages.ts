/** LLM ↔ UI 계약: 백엔드가 이 형태의 messages 배열을 내려 주고, 프론트는 타입별로 컴포넌트를 그린다.
 *  API 명세가 오면 이 파일만 맞추면 된다. */

export type Verdict = "urgent" | "possible" | "conditional" | "other_route" | "not_possible";

export interface ChoiceOption { id: string; label: string }

export type UiMessage =
  | { type: "text"; body: string }
  | { type: "choice"; question: string; options: ChoiceOption[]; allow_free_text?: boolean; help?: string }
  | { type: "photo_request"; instruction: string; must_include?: string[]; timer_sec?: number }
  | { type: "checklist"; items: { label: string; status: "ok" | "fail" | "unknown"; fix?: string }[] }
  | { type: "verdict_card"; verdict: Verdict; title: string; reasons: string[]; source_label?: string; next_actions: { id: string; label: string }[] }
  | { type: "step_guide"; step_no: number; total: number; screen: string; action: string; tip?: string; image_ref?: string }
  | { type: "draft_card"; text: string }
  | { type: "alert"; level: "info" | "warn" | "urgent"; body: string; call_number?: string };

export interface ChatTurn {
  id: string;
  role: "bot" | "user";
  messages: UiMessage[];
  createdAt: string;
}

export interface CaseRecord {
  id: string;
  createdAt: string;
  region: string;
  category: string;
  categoryLabel: string;
  verdict: Verdict;
  channel?: string;
  draftText?: string;
  userStatus: "submitted" | "not_submitted" | "pending";
  outcome?: "accepted" | "rejected" | "pending" | "unknown";
}

export interface SharedCase {
  id: string;
  verdict: Verdict;
  outcome: "accepted" | "rejected" | "other_route";
  categoryLabel: string;
  zoneLabel?: string;
  regionLabel: string;
  summary: string;
  lesson: string;
}

export const VERDICT_META: Record<Verdict, { label: string; badge: string; mark: string }> = {
  urgent:       { label: "긴급",       badge: "badge-urgent", mark: "!" },
  possible:     { label: "신고 가능",  badge: "badge-ok",     mark: "✓" },
  conditional:  { label: "조건부 가능", badge: "badge-warn",   mark: "△" },
  other_route:  { label: "다른 경로",  badge: "badge-route",  mark: "↪" },
  not_possible: { label: "신고 불가",  badge: "badge-stop",   mark: "✕" },
};
