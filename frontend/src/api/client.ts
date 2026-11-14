/** 백엔드 호출의 공통 입구. 화면은 fetch를 직접 쓰지 않고 여기의 api()만 쓴다. (docs/api-spec.md 1장) */

/** 기본값은 빈 문자열(같은 출처). 개발 중에는 Vite 프록시가 /api를 백엔드(8000)로 넘기고, 운영에서는 같은 도메인의 FastAPI가 받는다. */
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

const DEVICE_KEY = "shingomate.deviceId";

/** 익명 기기 ID(UUID v4). 첫 접속 때 만들어 localStorage에 둔다. */
export function getDeviceId(): string {
  try {
    const saved = localStorage.getItem(DEVICE_KEY);
    if (saved) return saved;
    const id = crypto.randomUUID();
    localStorage.setItem(DEVICE_KEY, id);
    return id;
  } catch {
    // localStorage를 쓸 수 없는 환경(사생활 보호 모드 등)에서는 새로고침 전까지만 유지한다.
    return (memoryId ??= crypto.randomUUID());
  }
}
let memoryId: string | undefined;

/** 백엔드 오류 응답 `{ detail, code }`. detail은 화면에 그대로 보여 줄 수 있는 해요체 문구다. */
export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const NETWORK_MESSAGE = "서버에 연결하지 못했어요. 인터넷 연결을 확인하고 다시 시도해 주세요.";

/** 어떤 오류든 화면에 보여 줄 문구로 바꾼다. */
export function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : NETWORK_MESSAGE;
}

export interface ApiOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  /** 객체는 JSON으로, FormData는 multipart/form-data로 보낸다. */
  body?: unknown;
  signal?: AbortSignal;
}

export async function api<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, signal } = opts;
  const headers: Record<string, string> = { "X-Device-Id": getDeviceId() };
  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body; // Content-Type은 브라우저가 boundary와 함께 정한다. 직접 넣으면 업로드가 깨진다.
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: payload, signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, "network_error", NETWORK_MESSAGE);
  }

  if (!res.ok) {
    let detail = "";
    let code = "unknown";
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
      if (typeof data?.code === "string") code = data.code;
    } catch {
      /* JSON이 아닌 오류 응답(프록시 오류 등)은 아래 기본 문구를 쓴다. */
    }
    throw new ApiError(res.status, code, detail || "문제가 생겼어요. 잠시 뒤 다시 시도해 주세요.");
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
