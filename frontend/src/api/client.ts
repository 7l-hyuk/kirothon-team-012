/** 백엔드 연동 자리. API 명세가 확정되면 여기만 고친다. */
/** 기본값은 빈 문자열(같은 출처). 개발 중에는 Vite 프록시가 /api를 백엔드(8000)로 넘기고, 운영에서는 같은 도메인의 FastAPI가 받는다. */
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}
